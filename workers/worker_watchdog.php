#!/usr/bin/env php
<?php
if(PHP_SAPI!=='cli')exit(1);require __DIR__.'/../includes/bootstrap.php';
$minutes=max(2,(int)music_setting($mysqli,'worker_timeout_minutes','20'));
$stmt=$mysqli->prepare("SELECT worker_id,status,heartbeat_at,GREATEST(0,TIMESTAMPDIFF(SECOND,heartbeat_at,NOW())) AS age_seconds FROM music_ai_workers WHERE status<>'STOPPED' ORDER BY heartbeat_at DESC LIMIT 1");$stmt->execute();$worker=$stmt->get_result()->fetch_assoc();$stmt->close();
if(!$worker){fwrite(STDERR,"Nenhum heartbeat do worker musical.\n");exit(1);}
$age=(int)$worker['age_seconds'];if($age>$minutes*60){fwrite(STDERR,"Heartbeat musical vencido.\n");exit(1);}echo "Heartbeat musical saudável.\n";
