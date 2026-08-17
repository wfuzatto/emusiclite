#!/usr/bin/env php
<?php
if (PHP_SAPI !== 'cli') exit(1);
require __DIR__ . '/../includes/bootstrap.php';
require_once __DIR__ . '/../services/DailyMusicAgentService.php';
$agent = new DailyMusicAgentService($mysqli);
$result = in_array('--now', $argv, true) ? $agent->createManual(0) : $agent->runScheduledIfDue();
echo json_encode($result ?: ['created'=>false,'reason'=>'not_due'], JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES) . PHP_EOL;
