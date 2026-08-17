<?php
// Usage:
// php track_importer.php "https://site.com/track.mp3" --title="" --artist="" --genre="" --mood="" --cover="" --out="../import_tracks.sql"

if ($argc < 2) {
    fwrite(STDERR, "Uso: php track_importer.php <URL> [--title=] [--artist=] [--genre=] [--mood=] [--cover=] [--out=]\n");
    exit(1);
}

$url = $argv[1];
$options = [
    'title' => 'Faixa importada',
    'artist' => 'Artista desconhecido',
    'genre' => 'Pop',
    'mood' => 'Leve',
    'cover' => '',
    'out' => __DIR__ . '/../import_tracks.sql',
];

foreach ($argv as $arg) {
    if (strpos($arg, '--title=') === 0) $options['title'] = substr($arg, 8);
    if (strpos($arg, '--artist=') === 0) $options['artist'] = substr($arg, 9);
    if (strpos($arg, '--genre=') === 0) $options['genre'] = substr($arg, 8);
    if (strpos($arg, '--mood=') === 0) $options['mood'] = substr($arg, 7);
    if (strpos($arg, '--cover=') === 0) $options['cover'] = substr($arg, 8);
    if (strpos($arg, '--out=') === 0) $options['out'] = substr($arg, 6);
}

function sql_escape($v) {
    $v = str_replace("\\", "\\\\", $v);
    $v = str_replace("'", "\\'", $v);
    return $v;
}

$insert = "INSERT INTO tracks (title, artist, genre, mood, description, duration, cover_url, stream_url) VALUES (" .
    "'" . sql_escape($options['title']) . "', " .
    "'" . sql_escape($options['artist']) . "', " .
    "'" . sql_escape($options['genre']) . "', " .
    "'" . sql_escape($options['mood']) . "', " .
    "'Importado por URL: " . sql_escape($url) . "', " .
    "'0:00', " .
    "'" . sql_escape($options['cover']) . "', " .
    "'" . sql_escape($url) . "');\n";

file_put_contents($options['out'], $insert, FILE_APPEND | LOCK_EX);

fwrite(STDOUT, "OK: adicionado em {$options['out']}\n");
