#!/usr/bin/env php
<?php

if (PHP_SAPI !== 'cli') exit(1);
require __DIR__ . '/../includes/bootstrap.php';
require_once __DIR__ . '/../services/MusicPipelineService.php';
require_once __DIR__ . '/../services/DailyMusicAgentService.php';

$config = music_config(); date_default_timezone_set($config['timezone']);
$daemon = in_array('--daemon', $argv, true); $once = in_array('--once', $argv, true);
$workerId = mb_substr((gethostname() ?: 'music-worker') . ':' . getmypid() . ':' . bin2hex(random_bytes(4)), 0, 100);
$queue = new QueueService($mysqli); $running = true;
if (function_exists('pcntl_async_signals')) {
    pcntl_async_signals(true);
    pcntl_signal(SIGTERM, static function () use (&$running): void { $running = false; });
    pcntl_signal(SIGINT, static function () use (&$running): void { $running = false; });
}

function music_worker_health(mysqli $db, array $config): array
{
    $text = (new TextGenerationService($db, $config))->healthCheck();
    $music = MusicGenerationFactory::create($config)->healthCheck();
    $comfy = (new ComfyCoverService($config))->healthCheck();
    return ['text_online'=>(bool)$text['online'],'text_model_available'=>(bool)$text['model_available'],'music_online'=>(bool)$music['online'],'music_configured'=>(bool)$music['configured'],'comfy_online'=>(bool)$comfy['online'],'checked_at'=>date(DATE_ATOM)];
}

function music_worker_error(mysqli $db, array $job, string $code, string $message, bool $permanent): void
{
    $trackId=(int)$job['track_id'];$jobId=(int)$job['id'];$userId=(int)$job['user_id'];$safe=mb_substr($message,0,500);
    $public = $permanent ? 'A criação foi interrompida por uma validação ou configuração que exige revisão.' : 'Falha técnica temporária; uma nova tentativa foi agendada.';
    $status = $permanent ? 'FAILED' : 'QUEUED';
    $stmt=$db->prepare('UPDATE music_ai_tracks SET status=?,is_published=0,published_at=NULL,last_error=? WHERE id=?');$stmt->bind_param('ssi',$status,$public,$trackId);$stmt->execute();$stmt->close();
    $metadata=json_encode(['attempt'=>(int)$job['attempts']],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
    $stmt=$db->prepare("INSERT INTO music_ai_logs(user_id,track_id,job_id,operation,status,error_code,error_message,metadata) VALUES(?,?,?,'pipeline',?,?,?,?)");$logStatus=$permanent?'failed':'retry';$stmt->bind_param('iiissss',$userId,$trackId,$jobId,$logStatus,$code,$safe,$metadata);$stmt->execute();$stmt->close();
    if(!empty($job['agent_run_id'])){$run=(int)$job['agent_run_id'];$runStatus=$permanent?'FAILED':'RECOVERING';$stmt=$db->prepare('UPDATE music_ai_agent_runs SET status=?,current_stage=?,error_message=?,recoveries=recoveries+1,next_recovery_at=IF(?=\'RECOVERING\',(SELECT next_attempt_at FROM music_ai_jobs WHERE id=?),NULL),last_heartbeat_at=NOW(),finished_at=IF(?=\'FAILED\',NOW(),NULL) WHERE id=?');$stmt->bind_param('ssssisi',$runStatus,$public,$safe,$runStatus,$jobId,$runStatus,$run);$stmt->execute();$stmt->close();}
}

$queue->heartbeat($workerId, 'STARTING', null, null, 'Inicializando', []);
$lastMaintenance = 0;
try {
    while ($running) {
        $maintenance = max(10, (int) music_setting($mysqli, 'worker_maintenance_seconds', '30'));
        if (time() - $lastMaintenance >= $maintenance) {
            $queue->recoverStoppedWorkers(); $queue->recoverStale((int) music_setting($mysqli, 'worker_timeout_minutes', (string)$config['worker_timeout_minutes']));
            $dailyAgent = new DailyMusicAgentService($mysqli);
            try { $dailyAgent->runScheduledIfDue(); }
            catch (Throwable $e) { error_log('[MusicLite] O agente diário não pôde iniciar; o worker continuará processando a fila existente.'); }
            try { $dailyAgent->reconcile(); }
            catch (Throwable $e) { error_log('[MusicLite] A reconciliação editorial falhou; o worker continuará ativo.'); }
            $queue->heartbeat($workerId, 'IDLE', null, null, 'Aguardando trabalho', music_worker_health($mysqli, $config)); $lastMaintenance = time();
        }
        $job = $queue->claim($workerId);
        if (!$job) { if ($once || !$daemon) break; usleep(1000000); continue; }
        try {
            $queue->heartbeat($workerId, 'PROCESSING', (int)$job['id'], (int)$job['track_id'], 'Iniciando trabalho', music_worker_health($mysqli, $config));
            $result=(new MusicPipelineService($mysqli,$config,$queue,$workerId))->process($job);$queue->complete((int)$job['id'],$result);
        } catch (MusicResourceBusyException $e) {
            $queue->deferForResources((int)$job['id'],$e->getMessage(),120);
        } catch (MusicPermanentException|InvalidArgumentException|DomainException $e) {
            $queue->fail((int)$job['id'],'PERMANENT_VALIDATION',$e->getMessage(),true,(int)$job['attempts']);music_worker_error($mysqli,$job,'PERMANENT_VALIDATION',$e->getMessage(),true);
        } catch (Throwable $e) {
            $queue->fail((int)$job['id'],'TRANSIENT_FAILURE',$e->getMessage(),false,(int)$job['attempts']);music_worker_error($mysqli,$job,'TRANSIENT_FAILURE',$e->getMessage(),false);
        }
        $queue->heartbeat($workerId, 'IDLE', null, null, 'Aguardando trabalho', music_worker_health($mysqli, $config));
        if ($once || !$daemon) break;
    }
} finally {
    $queue->heartbeat($workerId, 'STOPPED', null, null, 'Worker encerrado', []);
    $queue->recoverStoppedWorkers();
}
