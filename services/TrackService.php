<?php

require_once __DIR__ . '/ModerationService.php';
require_once __DIR__ . '/QueueService.php';

class TrackService
{
    public function __construct(private mysqli $db) {}

    public function create(int $userId, array $input, array $context = []): int
    {
        (new ModerationService())->validate($input);
        $required = ['genre','mood','theme','language','composition_type','original_idea'];
        foreach ($required as $key) {
            if (trim((string) ($input[$key] ?? '')) === '') throw new InvalidArgumentException('Preencha todos os campos obrigatórios.');
        }
        if (!in_array($input['composition_type'], ['INSTRUMENTAL','VOCAL'], true)) throw new InvalidArgumentException('Tipo de composição inválido.');
        $duration = max(30, min(180, (int) ($input['desired_duration_seconds'] ?? 180)));
        $bpm = !empty($input['bpm']) ? max(40, min(240, (int) $input['bpm'])) : null;
        $source = ($context['source'] ?? 'USER') === 'AGENT' ? 'AGENT' : 'USER';
        $generationModel = trim((string) ($input['generation_model'] ?? 'turbo'));
        if (!in_array($generationModel, ['turbo','shift1','shift3'], true)) throw new InvalidArgumentException('Modelo de geração inválido.');
        $generationState = json_encode(['generation_model' => $generationModel], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $fields = [];
        foreach (['genre','subgenre','mood','theme','language','composition_type','voice_type','instruments','descriptive_references','original_idea'] as $key) {
            $fields[$key] = mb_substr(trim((string) ($input[$key] ?? '')), 0, $key === 'original_idea' ? 8000 : ($key === 'instruments' || $key === 'descriptive_references' ? 3000 : 255));
        }
        $stmt = $this->db->prepare("INSERT INTO music_ai_tracks(owner_user_id,source,genre,subgenre,mood,theme,language,composition_type,desired_duration_seconds,bpm,voice_type,instruments,descriptive_references,original_idea,generation_state,status,current_stage,progress_percent) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'QUEUED','Projeto criado',5)");
        $stmt->bind_param('isssssssiisssss', $userId, $source, $fields['genre'], $fields['subgenre'], $fields['mood'], $fields['theme'], $fields['language'], $fields['composition_type'], $duration, $bpm, $fields['voice_type'], $fields['instruments'], $fields['descriptive_references'], $fields['original_idea'], $generationState);
        $stmt->execute(); $trackId = (int) $stmt->insert_id; $stmt->close();
        try {
            (new QueueService($this->db))->enqueue($userId, $trackId, (string) ($context['operation_key'] ?? 'track:pipeline:' . $trackId), 'PIPELINE', $context, $context['agent_run_id'] ?? null);
        } catch (Throwable $e) {
            $stmt = $this->db->prepare('DELETE FROM music_ai_tracks WHERE id=?'); $stmt->bind_param('i', $trackId); $stmt->execute(); $stmt->close(); throw $e;
        }
        return $trackId;
    }

    public function savePlan(int $trackId, array $plan): void
    {
        foreach (['title','description','genre','mood','bpm','key','duration_seconds','structure','instruments','lyrical_concept','audio_prompt','cover_prompt'] as $key) {
            if (!array_key_exists($key, $plan)) throw new MusicPermanentException('Planejamento musical incompleto.');
        }
        $json = json_encode($plan, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $structure = json_encode($plan['structure'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $audioPrompt = trim((string) $plan['audio_prompt']);
        $coverPrompt = trim((string) $plan['cover_prompt']);
        $stmt = $this->db->prepare("INSERT INTO music_ai_track_plans(track_id,plan_json,audio_prompt,cover_prompt,structure_json) VALUES(?,?,?,?,?) ON DUPLICATE KEY UPDATE plan_json=VALUES(plan_json),audio_prompt=VALUES(audio_prompt),cover_prompt=VALUES(cover_prompt),structure_json=VALUES(structure_json)");
        $stmt->bind_param('issss', $trackId, $json, $audioPrompt, $coverPrompt, $structure); $stmt->execute(); $stmt->close();
        $title = mb_substr(trim((string) $plan['title']), 0, 200);
        $description = mb_substr(trim((string) $plan['description']), 0, 5000);
        $stmt = $this->db->prepare("UPDATE music_ai_tracks SET title=?,description=?,plan_saved_at=COALESCE(plan_saved_at,NOW()),current_stage='Planejamento salvo',progress_percent=20,status='GENERATING',last_error=NULL WHERE id=?");
        $stmt->bind_param('ssi', $title, $description, $trackId); $stmt->execute(); $stmt->close();
    }

    public function saveLyrics(int $trackId, string $concept, ?string $lyrics, string $language, bool $instrumental): void
    {
        $stmt = $this->db->prepare("INSERT INTO music_ai_lyrics(track_id,concept_text,lyrics_text,language,is_instrumental) VALUES(?,?,?,?,?) ON DUPLICATE KEY UPDATE concept_text=VALUES(concept_text),lyrics_text=VALUES(lyrics_text),language=VALUES(language),is_instrumental=VALUES(is_instrumental)");
        $flag = $instrumental ? 1 : 0;
        $stmt->bind_param('isssi', $trackId, $concept, $lyrics, $language, $flag); $stmt->execute(); $stmt->close();
        $stmt = $this->db->prepare("UPDATE music_ai_tracks SET lyrics_saved_at=COALESCE(lyrics_saved_at,NOW()),current_stage='Letra salva',progress_percent=30 WHERE id=?");
        $stmt->bind_param('i', $trackId); $stmt->execute(); $stmt->close();
    }

    public function markPromptSaved(int $trackId): void
    {
        $stmt = $this->db->prepare("UPDATE music_ai_tracks SET prompt_saved_at=COALESCE(prompt_saved_at,NOW()),current_stage='Prompt musical salvo',progress_percent=35 WHERE id=? AND EXISTS(SELECT 1 FROM music_ai_track_plans p WHERE p.track_id=music_ai_tracks.id AND p.audio_prompt<>'')");
        $stmt->bind_param('i', $trackId); $stmt->execute();
        if ($stmt->affected_rows !== 1) { $stmt->close(); throw new MusicPermanentException('Prompt musical persistido não encontrado.'); }
        $stmt->close();
    }

    public function markCheckpoint(int $trackId, string $column, string $stage, int $percent, array $state = []): void
    {
        $allowed = ['audio_generated_at','audio_validated_at','audio_uploaded_at','cover_generated_at','cover_uploaded_at','publication_completed_at'];
        if (!in_array($column, $allowed, true)) throw new InvalidArgumentException('Checkpoint inválido.');
        $json = $state ? json_encode($state, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) : null;
        $sql = "UPDATE music_ai_tracks SET {$column}=COALESCE({$column},NOW()),current_stage=?,progress_percent=?,generation_state=COALESCE(?,generation_state),last_error=NULL WHERE id=?";
        $stmt = $this->db->prepare($sql); $stmt->bind_param('sisi', $stage, $percent, $json, $trackId); $stmt->execute(); $stmt->close();
    }

    public function publish(int $trackId, int $ownerId): void
    {
        $stmt = $this->db->prepare("UPDATE music_ai_tracks SET is_published=1,published_at=COALESCE(published_at,NOW()),publication_completed_at=COALESCE(publication_completed_at,NOW()),current_stage='Publicação concluída',progress_percent=100 WHERE id=? AND owner_user_id=? AND status='COMPLETED' AND audio_media_id IS NOT NULL AND cover_media_id IS NOT NULL");
        $stmt->bind_param('ii', $trackId, $ownerId); $stmt->execute();
        if ($stmt->affected_rows !== 1) { $stmt->close(); throw new MusicPermanentException('A música ainda não possui todos os itens necessários para publicação.'); }
        $stmt->close();
    }
}
