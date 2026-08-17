#!/usr/bin/env php
<?php
if(PHP_SAPI!=='cli'||$argc<6)exit(1);require __DIR__.'/../includes/bootstrap.php';require_once __DIR__.'/../services/QueueService.php';
$workerId=mb_substr((string)$argv[1],0,100);$jobId=(int)$argv[2];$trackId=(int)$argv[3];$stage=mb_substr((string)$argv[4],0,190);$parentPid=(int)$argv[5];
$queue=new QueueService($mysqli);while($parentPid>1&&is_dir('/proc/'.$parentPid)){$queue->touchJob($jobId,$workerId);$queue->heartbeat($workerId,'PROCESSING',$jobId,$trackId,$stage,null);sleep(15);}
