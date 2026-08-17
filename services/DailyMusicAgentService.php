<?php

require_once __DIR__ . '/TrackService.php';

class DailyMusicAgentService
{
    public function __construct(private mysqli $db) {}

    public function runScheduledIfDue(): ?array
    {
        if (music_setting($this->db, 'daily_agent_enabled', '1') !== '1') return null;
        $config = music_config();
        $zone = new DateTimeZone($config['timezone']);
        $now = new DateTimeImmutable('now', $zone);
        $time = music_setting($this->db, 'daily_agent_time', '04:30');
        if (!preg_match('/^(?:[01]\d|2[0-3]):[0-5]\d$/', $time) || $now->format('H:i') < $time) return null;
        return $this->create('DAILY', 'daily:' . $now->format('Y-m-d'), $now->format('Y-m-d'), null);
    }

    public function createManual(int $adminUserId): array
    {
        return $this->create('MANUAL', 'manual:' . $this->uuid(), null, $adminUserId);
    }

    public function reconcile(): int
    {
        $stmt = $this->db->prepare("SELECT r.id,r.track_id,r.status run_status,t.status track_status,t.current_stage,t.progress_percent,t.is_published,t.last_error FROM music_ai_agent_runs r LEFT JOIN music_ai_tracks t ON t.id=r.track_id WHERE r.status IN ('QUEUED','RUNNING','RECOVERING') ORDER BY r.id LIMIT 20");
        $stmt->execute(); $rows = $stmt->get_result(); $count = 0;
        while ($row = $rows->fetch_assoc()) {
            $count++; $runId = (int) $row['id'];
            if ($row['track_status'] === 'COMPLETED' && (int) $row['is_published'] === 1) {
                $update = $this->db->prepare("UPDATE music_ai_agent_runs SET status='COMPLETED',current_stage='Publicação concluída',progress_percent=100,error_message=NULL,finished_at=COALESCE(finished_at,NOW()),last_heartbeat_at=NOW() WHERE id=?");
            } elseif ($row['track_status'] === 'FAILED') {
                $update = $this->db->prepare("UPDATE music_ai_agent_runs SET status='FAILED',current_stage='Falha definitiva',error_message=?,finished_at=NOW(),last_heartbeat_at=NOW() WHERE id=?");
                $error = mb_substr((string) $row['last_error'], 0, 500); $update->bind_param('si', $error, $runId); $update->execute(); $update->close(); continue;
            } else {
                $nextStatus = $row['run_status'] === 'RECOVERING' ? 'RECOVERING' : 'RUNNING';
                $update = $this->db->prepare("UPDATE music_ai_agent_runs SET status=?,current_stage=?,progress_percent=?,last_heartbeat_at=NOW() WHERE id=?");
                $stage = (string) ($row['current_stage'] ?: 'Na fila'); $progress = (int) ($row['progress_percent'] ?? 0); $update->bind_param('ssii', $nextStatus, $stage, $progress, $runId); $update->execute(); $update->close(); continue;
            }
            $update->bind_param('i', $runId); $update->execute(); $update->close();
        }
        $stmt->close();
        return $count;
    }

    public function resume(int $runId): void
    {
        $stmt = $this->db->prepare("SELECT r.track_id,r.owner_user_id FROM music_ai_agent_runs r WHERE r.id=? AND r.status IN ('RECOVERING','FAILED','RUNNING') LIMIT 1");
        $stmt->bind_param('i', $runId); $stmt->execute(); $run = $stmt->get_result()->fetch_assoc(); $stmt->close();
        if (!$run) throw new RuntimeException('Execução não encontrada.');
        $trackId = (int) $run['track_id']; $owner = (int) $run['owner_user_id'];
        (new QueueService($this->db))->enqueue($owner, $trackId, 'agent:pipeline:' . $runId, 'PIPELINE', ['source' => 'AGENT','agent_run_id' => $runId,'auto_publish' => true], $runId);
        $stmt = $this->db->prepare("UPDATE music_ai_agent_runs SET status='RECOVERING',next_recovery_at=NOW(),recoveries=recoveries+1,finished_at=NULL WHERE id=?");
        $stmt->bind_param('i', $runId); $stmt->execute(); $stmt->close();
    }

    private function create(string $trigger, string $key, ?string $day, ?int $triggeredBy): array
    {
        $stmt = $this->db->prepare('SELECT id,track_id,status FROM music_ai_agent_runs WHERE run_key=? LIMIT 1');
        $stmt->bind_param('s', $key); $stmt->execute(); $existing = $stmt->get_result()->fetch_assoc(); $stmt->close();
        if ($existing) return ['created' => false, 'run' => $existing];
        $owner = $this->agentOwnerId();
        $stmt = $this->db->prepare("INSERT INTO music_ai_agent_runs(run_key,trigger_type,scheduled_for,triggered_by,owner_user_id,status,current_stage) VALUES(?,?,?,?,?,'QUEUED','Preparando ideia')");
        $stmt->bind_param('sssii', $key, $trigger, $day, $triggeredBy, $owner);
        try { $stmt->execute(); $runId = (int) $stmt->insert_id; $stmt->close(); }
        catch (mysqli_sql_exception $e) { $stmt->close(); if ((int) $e->getCode() === 1062) return $this->create($trigger, $key, $day, $triggeredBy); throw $e; }
        try {
            $input = $this->randomBrief();
            $trackId = (new TrackService($this->db))->create($owner, $input, ['source' => 'AGENT','agent_run_id' => $runId,'operation_key' => 'agent:pipeline:' . $runId,'auto_publish' => music_setting($this->db, 'daily_agent_auto_publish', '1') === '1']);
            $payload = json_encode($input, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            $stmt = $this->db->prepare("UPDATE music_ai_agent_runs SET track_id=?,status='RUNNING',current_stage='Planejamento na fila',progress_percent=5,payload=?,started_at=NOW(),last_heartbeat_at=NOW() WHERE id=?");
            $stmt->bind_param('isi', $trackId, $payload, $runId); $stmt->execute(); $stmt->close();
            return ['created' => true, 'run_id' => $runId, 'track_id' => $trackId];
        } catch (Throwable $e) {
            $message = mb_substr($e->getMessage(), 0, 500);
            $stmt = $this->db->prepare("UPDATE music_ai_agent_runs SET status='FAILED',current_stage='Falha ao iniciar',error_message=?,finished_at=NOW() WHERE id=?");
            $stmt->bind_param('si', $message, $runId); $stmt->execute(); $stmt->close(); throw $e;
        }
    }

    private function agentOwnerId(): int
    {
        $code = 'AGENTE-MUSICAL';
        $stmt = $this->db->prepare("SELECT id FROM music_ai_users WHERE internal_code=? AND user_type='SYSTEM' AND status='SYSTEM' LIMIT 1");
        $stmt->bind_param('s', $code); $stmt->execute(); $row = $stmt->get_result()->fetch_assoc(); $stmt->close();
        if (!$row) throw new RuntimeException('Usuário técnico AGENTE-MUSICAL não foi criado pela migration.');
        return (int) $row['id'];
    }

    private function randomBrief(): array
    {
        $genres = array_values(array_filter(array_map('trim', explode(',', music_setting($this->db, 'daily_agent_genres', 'Pop,MPB,Eletrônica,Jazz,Lo-fi')))));
        $types = array_values(array_intersect(['INSTRUMENTAL','VOCAL'], array_map('trim', explode(',', music_setting($this->db, 'daily_agent_composition_types', 'INSTRUMENTAL,VOCAL')))));
        if (!$genres || !$types) throw new RuntimeException('Preferências editoriais do agente estão vazias.');
        $pick = static fn(array $items) => $items[random_int(0, count($items) - 1)];
        $themes = ['recomeços em uma manhã chuvosa','uma viagem por paisagens brasileiras imaginárias','amizade que atravessa mudanças','a tranquilidade de observar as estrelas','uma cidade que desperta ao amanhecer','memórias felizes de um verão inventado'];
        $moods = ['esperançoso','contemplativo','energético','sereno','dançante','cinematográfico'];
        $instruments = ['violão, baixo e percussão leve','piano, cordas e bateria acústica','sintetizadores, baixo eletrônico e pads','guitarra limpa, bateria e teclados','piano elétrico, contrabaixo e saxofone','percussões brasileiras, flauta e violão'];
        $type = $pick($types); $theme = $pick($themes); $genre = $pick($genres); $mood = $pick($moods); $instrument = $pick($instruments);
        return [
            'genre' => $genre, 'subgenre' => '', 'mood' => $mood, 'theme' => $theme, 'language' => 'Português',
            'composition_type' => $type, 'desired_duration_seconds' => max(30, min(600, (int) music_setting($this->db, 'daily_agent_duration_seconds', '180'))),
            'bpm' => null, 'voice_type' => $type === 'VOCAL' ? $pick(['voz suave','voz quente','dueto equilibrado']) : '',
            'instruments' => $instrument, 'descriptive_references' => 'Composição original; referências apenas de textura, andamento e instrumentação.',
            'original_idea' => "Crie uma música completamente original de {$genre}, com clima {$mood}, sobre {$theme}. Use {$instrument}. Trabalhe somente com referências abstratas de textura, andamento e instrumentação.",
        ];
    }

    private function uuid(): string { return bin2hex(random_bytes(16)); }
}
