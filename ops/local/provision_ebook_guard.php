#!/usr/bin/env php
<?php

declare(strict_types=1);

$password = (string) getenv('MUSIC_GUARD_PASSWORD');
if (strlen($password) < 32) {
    throw new RuntimeException('MUSIC_GUARD_PASSWORD inválida.');
}

require '/opt/ebooklite/includes/db.php';

$identity = (string) $mysqli->query('SELECT USER()')->fetch_row()[0];
$separator = strrpos($identity, '@');
$sourceHost = $separator === false ? '' : substr($identity, $separator + 1);
$database = (string) $mysqli->query('SELECT DATABASE()')->fetch_row()[0];
if ($sourceHost === '' || $database === '') {
    throw new RuntimeException('Origem ou banco do eBookLite não identificado.');
}

$safeDatabase = str_replace('`', '``', $database);
$safeUser = $mysqli->real_escape_string('musiclite_guard');
$safeHost = $mysqli->real_escape_string($sourceHost);
$safePassword = $mysqli->real_escape_string($password);
$account = "'{$safeUser}'@'{$safeHost}'";

foreach (['ebook_ai_jobs', 'ebook_ai_settings'] as $table) {
    $mysqli->query(
        "GRANT SELECT ON `{$safeDatabase}`.`{$table}` TO {$account} IDENTIFIED BY '{$safePassword}'"
    );
}

$check = new mysqli(
    (string) getenv('EBOOK_DB_HOST'),
    'musiclite_guard',
    $password,
    $database,
    (int) (getenv('EBOOK_DB_PORT') ?: 3306)
);
$check->set_charset('utf8mb4');
$count = $check->query("SELECT COUNT(*) FROM ebook_ai_jobs WHERE status='processing'")->fetch_row()[0];
$check->query("SELECT COUNT(*) FROM ebook_ai_settings")->fetch_row();
$check->close();

echo 'guard_ready=yes', PHP_EOL;
echo 'processing_jobs=', (int) $count, PHP_EOL;

