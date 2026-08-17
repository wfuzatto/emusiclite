#!/usr/bin/env php
<?php

declare(strict_types=1);

require '/opt/ebooklite/includes/db.php';

foreach (['ebook_ai_jobs', 'ebook_ai_workers', 'ebook_ai_settings'] as $table) {
    $quoted = '`' . str_replace('`', '``', $table) . '`';
    $result = $mysqli->query("SHOW TABLES LIKE '" . $mysqli->real_escape_string($table) . "'");
    $exists = $result && $result->num_rows === 1;
    echo $table, ':', $exists ? 'yes' : 'no', PHP_EOL;
    if (!$exists || $table !== 'ebook_ai_jobs') {
        continue;
    }

    $counts = $mysqli->query("SELECT status, COUNT(*) AS total FROM {$quoted} GROUP BY status ORDER BY status");
    while ($row = $counts->fetch_assoc()) {
        echo 'jobs_', (string) $row['status'], '=', (int) $row['total'], PHP_EOL;
    }

    $available = [];
    $columns = $mysqli->query("SHOW COLUMNS FROM {$quoted}");
    while ($column = $columns->fetch_assoc()) {
        $available[(string) $column['Field']] = true;
    }
    $selected = array_values(array_filter(
        ['id', 'book_id', 'job_type', 'status', 'current_stage', 'progress_percent', 'attempts', 'available_at', 'started_at', 'heartbeat_at', 'updated_at'],
        static fn(string $name): bool => isset($available[$name])
    ));
    if ($selected !== []) {
        $safeColumns = implode(',', array_map(static fn(string $name): string => "`{$name}`", $selected));
        $active = $mysqli->query("SELECT {$safeColumns} FROM {$quoted} WHERE status='processing' ORDER BY id LIMIT 10");
        while ($row = $active->fetch_assoc()) {
            echo 'processing_job=', json_encode($row, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), PHP_EOL;
        }
    }
}

$runs = $mysqli->query(
    "SELECT id,book_id,status,current_stage,last_heartbeat_at,next_recovery_at
     FROM ebook_ai_agent_runs
     WHERE status IN ('queued','running','recovering')
     ORDER BY id DESC LIMIT 5"
);
while ($row = $runs->fetch_assoc()) {
    echo 'active_agent_run=', json_encode($row, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), PHP_EOL;
}

$workers = $mysqli->query(
    "SELECT worker_id,status,current_job_id,heartbeat_at
     FROM ebook_ai_workers
     WHERE status IN ('starting','idle','processing')
     ORDER BY heartbeat_at DESC LIMIT 5"
);
while ($row = $workers->fetch_assoc()) {
    echo 'worker=', json_encode($row, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), PHP_EOL;
}
