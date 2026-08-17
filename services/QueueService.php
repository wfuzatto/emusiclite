<?php

require_once __DIR__ . '/MusicExceptions.php';

class QueueService
{
    public function __construct(private mysqli $db) {}

    public function enqueue(int $userId, int $trackId, string $operationKey, string $type = 'PIPELINE', array $payload = [], ?int $agentRunId = null): int
    {
        $json = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $stmt = $this->db->prepare(
            "INSERT INTO music_ai_jobs(user_id,track_id,agent_run_id,job_type,operation_key,payload)
             VALUES(?,?,?,?,?,?) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id),
             status=IF(status IN ('FAILED','CANCELLED'),'PENDING',status),
             attempts=IF(status IN ('FAILED','CANCELLED'),0,attempts),
             available_at=IF(status IN ('FAILED','CANCELLED'),NOW(),available_at),
             error_code=IF(status IN ('FAILED','CANCELLED'),NULL,error_code),
             error_message=IF(status IN ('FAILED','CANCELLED'),NULL,error_message)"
        );
        $stmt->bind_param('iiisss', $userId, $trackId, $agentRunId, $type, $operationKey, $json);
        $stmt->execute();
        $id = (int) $this->db->insert_id;
        $stmt->close();
        return $id;
    }

    public function claim(string $workerId): ?array
    {
        $this->db->begin_transaction();
        try {
            $row = $this->db->query("SELECT * FROM music_ai_jobs WHERE status='PENDING' AND available_at<=NOW() ORDER BY priority,id LIMIT 1 FOR UPDATE")->fetch_assoc();
            if (!$row) { $this->db->commit(); return null; }
            $id = (int) $row['id'];
            $stmt = $this->db->prepare("UPDATE music_ai_jobs SET status='PROCESSING',attempts=attempts+1,locked_by=?,started_at=NOW(),heartbeat_at=NOW(),next_attempt_at=NULL WHERE id=? AND status='PENDING'");
            $stmt->bind_param('si', $workerId, $id);
            $stmt->execute();
            if ($stmt->affected_rows !== 1) { $stmt->close(); $this->db->rollback(); return null; }
            $stmt->close();
            $this->db->commit();
            $row['attempts'] = (int) $row['attempts'] + 1;
            return $row;
        } catch (Throwable $e) {
            $this->db->rollback();
            throw $e;
        }
    }

    public function complete(int $jobId, array $result = []): void
    {
        $json = json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $stmt = $this->db->prepare("UPDATE music_ai_jobs SET status='COMPLETED',result_data=?,locked_by=NULL,error_code=NULL,error_message=NULL,finished_at=NOW() WHERE id=? AND status='PROCESSING'");
        $stmt->bind_param('si', $json, $jobId); $stmt->execute(); $stmt->close();
    }

    public function fail(int $jobId, string $code, string $message, bool $permanent, int $attempts): void
    {
        $message = mb_substr($message, 0, 500);
        if ($permanent) {
            $stmt = $this->db->prepare("UPDATE music_ai_jobs SET status='FAILED',error_code=?,error_message=?,locked_by=NULL,heartbeat_at=NULL,finished_at=NOW() WHERE id=?");
            $stmt->bind_param('ssi', $code, $message, $jobId);
        } else {
            $delays = [1 => 5, 2 => 15, 3 => 30, 4 => 60, 5 => 120, 6 => 240, 7 => 480, 8 => 960];
            $delay = $delays[$attempts] ?? 1800;
            $stmt = $this->db->prepare("UPDATE music_ai_jobs SET status='PENDING',error_code=?,error_message=?,locked_by=NULL,started_at=NULL,heartbeat_at=NULL,available_at=DATE_ADD(NOW(),INTERVAL ? SECOND),next_attempt_at=DATE_ADD(NOW(),INTERVAL ? SECOND) WHERE id=?");
            $stmt->bind_param('ssiii', $code, $message, $delay, $delay, $jobId);
        }
        $stmt->execute(); $stmt->close();
    }

    public function deferForResources(int $jobId, string $message, int $seconds = 120): void
    {
        $seconds = max(30, min(1800, $seconds));
        $stmt = $this->db->prepare("UPDATE music_ai_jobs SET status='PENDING',attempts=IF(attempts>0,attempts-1,0),error_code='RESOURCE_BUSY',error_message=?,locked_by=NULL,started_at=NULL,heartbeat_at=NULL,available_at=DATE_ADD(NOW(),INTERVAL ? SECOND),next_attempt_at=DATE_ADD(NOW(),INTERVAL ? SECOND) WHERE id=?");
        $stmt->bind_param('siii', $message, $seconds, $seconds, $jobId); $stmt->execute(); $stmt->close();
    }

    public function touchJob(int $jobId, string $workerId): void
    {
        $stmt = $this->db->prepare("UPDATE music_ai_jobs SET heartbeat_at=NOW() WHERE id=? AND locked_by=? AND status='PROCESSING'");
        $stmt->bind_param('is', $jobId, $workerId); $stmt->execute(); $stmt->close();
    }

    public function recoverStale(int $minutes): int
    {
        $minutes = max(5, $minutes);
        $stmt = $this->db->prepare("UPDATE music_ai_jobs SET status='PENDING',locked_by=NULL,started_at=NULL,heartbeat_at=NULL,available_at=NOW(),attempts=IF(attempts>0,attempts-1,0),error_code='WORKER_LOST',error_message='Trabalho recuperado após interrupção' WHERE status='PROCESSING' AND COALESCE(heartbeat_at,started_at)<DATE_SUB(NOW(),INTERVAL ? MINUTE)");
        $stmt->bind_param('i', $minutes); $stmt->execute(); $count = $stmt->affected_rows; $stmt->close(); return $count;
    }

    public function recoverStoppedWorkers(): int
    {
        $stmt = $this->db->prepare("UPDATE music_ai_jobs j JOIN music_ai_workers w ON w.worker_id=j.locked_by SET j.status='PENDING',j.locked_by=NULL,j.started_at=NULL,j.heartbeat_at=NULL,j.available_at=NOW(),j.attempts=IF(j.attempts>0,j.attempts-1,0),j.error_code='WORKER_STOPPED',j.error_message='Trabalho retomado após parada do worker' WHERE j.status='PROCESSING' AND w.status='STOPPED'");
        $stmt->execute(); $count = $stmt->affected_rows; $stmt->close(); return $count;
    }

    public function heartbeat(string $workerId, string $status, ?int $jobId = null, ?int $trackId = null, ?string $stage = null, ?array $health = null): void
    {
        $hostname = mb_substr((string) (gethostname() ?: 'music-worker'), 0, 190);
        $pid = (int) getmypid();
        $json = $health === null ? null : json_encode($health, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $stmt = $this->db->prepare("INSERT INTO music_ai_workers(worker_id,hostname,process_id,status,current_job_id,current_track_id,current_stage,health_json,started_at,heartbeat_at,stopped_at) VALUES(?,?,?,?,?,?,?,?,NOW(),NOW(),IF(?='STOPPED',NOW(),NULL)) ON DUPLICATE KEY UPDATE process_id=VALUES(process_id),status=VALUES(status),current_job_id=VALUES(current_job_id),current_track_id=VALUES(current_track_id),current_stage=VALUES(current_stage),health_json=COALESCE(VALUES(health_json),health_json),heartbeat_at=NOW(),stopped_at=IF(VALUES(status)='STOPPED',NOW(),NULL)");
        $stmt->bind_param('ssisiisss', $workerId, $hostname, $pid, $status, $jobId, $trackId, $stage, $json, $status);
        $stmt->execute(); $stmt->close();
    }
}
