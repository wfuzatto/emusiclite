#!/usr/bin/env php
<?php
if(PHP_SAPI!=='cli')exit(1);
try {
    require __DIR__.'/../includes/bootstrap.php';
    require_once __DIR__.'/../services/QueueService.php';
    $host=mb_substr((string)(gethostname()?:'music-worker'),0,190);
    $stmt=$mysqli->prepare("UPDATE music_ai_workers SET status='STOPPED',stopped_at=NOW(),heartbeat_at=NOW() WHERE hostname=? AND status<>'STOPPED'");
    $stmt->bind_param('s',$host);$stmt->execute();$stmt->close();
    $count=(new QueueService($mysqli))->recoverStoppedWorkers();
    echo"Jobs recuperados: {$count}\n";
} catch (Throwable $e) {
    // During a network outage the daemon must still be allowed to stop. The
    // watchdog will recover its durable jobs as soon as MySQL is reachable.
    fwrite(STDERR,"[AVISO] Encerramento sem banco; a recuperação será feita pelo watchdog.\n");
    exit(0);
}
