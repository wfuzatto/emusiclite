<?php

require_once __DIR__ . '/TrackService.php';
require_once __DIR__ . '/TextGenerationService.php';
require_once __DIR__ . '/MusicGenerationFactory.php';
require_once __DIR__ . '/AudioValidationService.php';
require_once __DIR__ . '/ComfyCoverService.php';
require_once __DIR__ . '/ResourceGuard.php';
require_once __DIR__ . '/IngestClient.php';

class MusicPipelineService
{
    private TrackService $tracks;
    public function __construct(private mysqli $db, private array $config, private QueueService $queue, private string $workerId)
    {
        $this->tracks = new TrackService($db);
    }

    public function process(array $job): array
    {
        $trackId = (int) $job['track_id']; $jobId = (int) $job['id'];
        $track = $this->loadTrack($trackId);
        if (!$track || $track['status'] === 'DELETED') throw new MusicPermanentException('Projeto musical não encontrado.');
        $dir = $this->config['storage_path'] . '/tracks/' . $trackId;
        if (!is_dir($dir) && !mkdir($dir, 0750, true) && !is_dir($dir)) throw new RuntimeException('Não foi possível preparar o diretório do projeto.');

        if (!$track['plan_saved_at']) {
            $this->stage($job, 'Aguardando recursos para planejar', 8);
            $plan = $this->withHeartbeat(
                $job,
                'Criando planejamento',
                fn() => (new ResourceGuard($this->db, $this->config))->withTextSlot(
                    fn() => (new TextGenerationService($this->db, $this->config))->plan($track)
                )
            );
            $this->tracks->savePlan($trackId, $plan);
            $track = $this->loadTrack($trackId);
        }
        $plan = $this->loadPlan($trackId);

        if (!$track['lyrics_saved_at']) {
            $instrumental = $track['composition_type'] === 'INSTRUMENTAL';
            $lyrics = $instrumental ? null : trim((string) ($plan['lyrics'] ?? ''));
            if (!$instrumental && $lyrics === '') {
                $this->stage($job, 'Criando letra', 25);
                $lyrics = $this->withHeartbeat(
                    $job,
                    'Criando letra',
                    fn() => (new ResourceGuard($this->db, $this->config))->withTextSlot(
                        fn() => (new TextGenerationService($this->db, $this->config))->generateLyrics($track, $plan)
                    )
                );
            }
            $this->stage($job, 'Salvando letra', 28);
            $this->tracks->saveLyrics($trackId, (string) $plan['lyrical_concept'], $lyrics, $track['language'], $instrumental);
            $track = $this->loadTrack($trackId);
        }

        if (!$track['prompt_saved_at']) {
            $this->stage($job, 'Persistindo prompt musical', 33);
            $this->tracks->markPromptSaved($trackId);
            $track = $this->loadTrack($trackId);
        }

        $state = json_decode((string) ($track['generation_state'] ?? ''), true) ?: [];
        $audioPath = (string) ($state['audio_path'] ?? ($dir . '/audio.generated'));
        if (!$track['audio_generated_at'] || !is_file($audioPath)) {
            if (!$track['audio_generated_at'] && is_file($audioPath) && filesize($audioPath) >= 1024) {
                $state = array_merge($state, ['audio_path' => $audioPath, 'recovered_existing_audio' => true]);
                $this->tracks->markCheckpoint($trackId, 'audio_generated_at', 'Áudio gerado recuperado', 60, $state);
            } else {
                $this->stage($job, 'Aguardando recursos para gerar áudio', 35);
                $lyrics = $this->loadLyrics($trackId);
                $spec = ['prompt' => $plan['audio_prompt'], 'lyrics' => $lyrics['lyrics_text'], 'instrumental' => $track['composition_type'] === 'INSTRUMENTAL', 'duration_seconds' => (int) $track['desired_duration_seconds'], 'genre' => $track['genre'], 'subgenre' => $track['subgenre'], 'mood' => $track['mood'], 'theme' => $track['theme'], 'language' => $track['language'], 'bpm' => $track['bpm'], 'key' => $plan['key'], 'voice_type' => $track['voice_type'], 'instruments' => $plan['instruments'], 'structure' => $plan['structure'], 'descriptive_references' => $track['descriptive_references']];
                $this->stage($job, 'Gerando áudio', 45);
                $result = $this->withHeartbeat($job, 'Gerando áudio', fn() => (new ResourceGuard($this->db, $this->config))->withHeavySlot(false, fn() => MusicGenerationFactory::create($this->config)->generate($spec, $audioPath)));
                $state = array_merge($state, ['audio_path' => $audioPath, 'audio_backend' => $result]);
                $this->tracks->markCheckpoint($trackId, 'audio_generated_at', 'Áudio gerado', 60, $state);
            }
            $track = $this->loadTrack($trackId);
        }

        if (!$track['audio_validated_at']) {
            $this->stage($job, 'Validando áudio', 65);
            $validation = (new AudioValidationService($this->config))->validate($audioPath, (int) $track['desired_duration_seconds']);
            $state = array_merge($state, ['audio_path' => $audioPath, 'audio_validation' => $validation]);
            $this->tracks->markCheckpoint($trackId, 'audio_validated_at', 'Áudio validado', 70, $state);
            $track = $this->loadTrack($trackId);
        }

        if (!$track['audio_uploaded_at'] || !$track['audio_media_id']) {
            $this->stage($job, 'Enviando áudio', 73);
            $mediaId = (new IngestClient($this->config))->upload('AUDIO', $trackId, (int) $track['owner_user_id'], $audioPath, $state['audio_validation'] ?? []);
            $stmt = $this->db->prepare('UPDATE music_ai_tracks SET audio_media_id=? WHERE id=?'); $stmt->bind_param('ii', $mediaId, $trackId); $stmt->execute(); $stmt->close();
            $this->tracks->markCheckpoint($trackId, 'audio_uploaded_at', 'Áudio armazenado', 78, $state);
            $track = $this->loadTrack($trackId);
        }

        $coverPath = (string) ($state['cover_path'] ?? ($dir . '/cover.png'));
        if (!$track['cover_generated_at'] || !is_file($coverPath)) {
            if (!$track['cover_generated_at'] && is_file($coverPath) && @getimagesize($coverPath)) {
                $size = getimagesize($coverPath); $state = array_merge($state, ['cover_path'=>$coverPath,'cover_validation'=>['width'=>$size[0],'height'=>$size[1],'sha256'=>hash_file('sha256',$coverPath)],'recovered_existing_cover'=>true]);
                $this->tracks->markCheckpoint($trackId, 'cover_generated_at', 'Capa gerada recuperada', 88, $state);
            } else {
                $this->stage($job, 'Aguardando recursos para gerar capa', 80);
                $this->stage($job, 'Gerando capa', 83);
                $cover = $this->withHeartbeat($job, 'Gerando capa', fn() => (new ResourceGuard($this->db, $this->config))->withHeavySlot(true, fn() => (new ComfyCoverService($this->config))->generate((string) $plan['cover_prompt'], $coverPath)));
                $state = array_merge($state, ['cover_path' => $coverPath, 'cover_validation' => $cover]);
                $this->tracks->markCheckpoint($trackId, 'cover_generated_at', 'Capa gerada', 88, $state);
            }
            $track = $this->loadTrack($trackId);
        }

        if (!$track['cover_uploaded_at'] || !$track['cover_media_id']) {
            $this->stage($job, 'Enviando capa', 90);
            $mediaId = (new IngestClient($this->config))->upload('COVER', $trackId, (int) $track['owner_user_id'], $coverPath, $state['cover_validation'] ?? []);
            $stmt = $this->db->prepare('UPDATE music_ai_tracks SET cover_media_id=? WHERE id=?'); $stmt->bind_param('ii', $mediaId, $trackId); $stmt->execute(); $stmt->close();
            $this->tracks->markCheckpoint($trackId, 'cover_uploaded_at', 'Capa armazenada', 94, $state);
            $track = $this->loadTrack($trackId);
        }

        $stmt = $this->db->prepare("UPDATE music_ai_tracks SET status='COMPLETED',current_stage='Pronta para publicar',progress_percent=95,last_error=NULL WHERE id=? AND audio_media_id IS NOT NULL AND cover_media_id IS NOT NULL");
        $stmt->bind_param('i', $trackId); $stmt->execute(); $stmt->close();
        $payload = json_decode((string) ($job['payload'] ?? ''), true) ?: [];
        if (!empty($payload['auto_publish']) && $track['source'] === 'AGENT') $this->tracks->publish($trackId, (int) $track['owner_user_id']);
        $this->updateAgent((int) ($job['agent_run_id'] ?? 0), $trackId);
        return ['track_id' => $trackId, 'completed' => true];
    }

    private function stage(array $job, string $stage, int $percent): void
    {
        $trackId = (int) $job['track_id']; $jobId = (int) $job['id'];
        $stmt = $this->db->prepare("UPDATE music_ai_tracks SET status='GENERATING',current_stage=?,progress_percent=? WHERE id=?");
        $stmt->bind_param('sii', $stage, $percent, $trackId); $stmt->execute(); $stmt->close();
        $this->queue->touchJob($jobId, $this->workerId);
        $this->queue->heartbeat($this->workerId, 'PROCESSING', $jobId, $trackId, $stage, null);
        if (!empty($job['agent_run_id'])) {
            $run = (int) $job['agent_run_id'];
            $stmt = $this->db->prepare("UPDATE music_ai_agent_runs SET status='RUNNING',current_stage=?,progress_percent=?,attempts=GREATEST(attempts,1),last_heartbeat_at=NOW() WHERE id=?");
            $stmt->bind_param('sii', $stage, $percent, $run); $stmt->execute(); $stmt->close();
        }
    }

    private function loadTrack(int $id): ?array { $stmt=$this->db->prepare('SELECT * FROM music_ai_tracks WHERE id=? LIMIT 1');$stmt->bind_param('i',$id);$stmt->execute();$row=$stmt->get_result()->fetch_assoc();$stmt->close();return $row?:null; }
    private function loadPlan(int $id): array { $stmt=$this->db->prepare('SELECT plan_json FROM music_ai_track_plans WHERE track_id=?');$stmt->bind_param('i',$id);$stmt->execute();$row=$stmt->get_result()->fetch_assoc();$stmt->close();$plan=json_decode((string)($row['plan_json']??''),true);if(!is_array($plan))throw new MusicPermanentException('Planejamento persistido inválido.');return $plan; }
    private function loadLyrics(int $id): array { $stmt=$this->db->prepare('SELECT * FROM music_ai_lyrics WHERE track_id=?');$stmt->bind_param('i',$id);$stmt->execute();$row=$stmt->get_result()->fetch_assoc();$stmt->close();if(!$row)throw new MusicPermanentException('Letra persistida não encontrada.');return $row; }
    private function updateAgent(int $runId, int $trackId): void { if($runId<1)return;$stmt=$this->db->prepare("UPDATE music_ai_agent_runs r JOIN music_ai_tracks t ON t.id=? SET r.status=IF(t.is_published=1,'COMPLETED','RUNNING'),r.current_stage=t.current_stage,r.progress_percent=t.progress_percent,r.error_message=NULL,r.last_heartbeat_at=NOW(),r.finished_at=IF(t.is_published=1,NOW(),NULL) WHERE r.id=?");$stmt->bind_param('ii',$trackId,$runId);$stmt->execute();$stmt->close(); }
    private function withHeartbeat(array $job, string $stage, callable $operation)
    {
        $process = null;
        if (function_exists('proc_open')) {
            $null = fopen('/dev/null', 'a');
            $process = @proc_open([PHP_BINARY,__DIR__.'/../workers/heartbeat_lease.php',$this->workerId,(string)(int)$job['id'],(string)(int)$job['track_id'],$stage,(string)getmypid()], [0=>['file','/dev/null','r'],1=>$null,2=>$null], $pipes);
            if (is_resource($null)) fclose($null);
        }
        try { return $operation(); }
        finally { if (is_resource($process)) { @proc_terminate($process); @proc_close($process); } }
    }
}
