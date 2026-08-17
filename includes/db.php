<?php
$DB_HOST = getenv('MUSIC_DB_HOST') ?: 'localhost';
$DB_PORT = (int) (getenv('MUSIC_DB_PORT') ?: 3306);
$DB_USER = getenv('MUSIC_DB_USER') ?: 'root';
$DB_PASS = getenv('MUSIC_DB_PASSWORD') ?: '';
$DB_NAME = getenv('MUSIC_DB_NAME') ?: 'emusic_lite';

$mysqli = new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
if ($mysqli->connect_errno) {
    throw new RuntimeException('Não foi possível conectar ao banco de dados.');
}
$mysqli->set_charset('utf8mb4');
