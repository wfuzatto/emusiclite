<?php

require_once __DIR__ . '/MusicExceptions.php';

class EbookQueueStatusService
{
    public function __construct(private mysqli $musicDb, private array $config) {}

    public function processingCount(): int
    {
        [$db, $owned] = $this->connection();
        try {
            $database = $this->databaseName($db);
            if (!$this->tableExists($db, $database, 'ebook_ai_jobs')) {
                throw new RuntimeException('Fila do eBookLite não encontrada.');
            }
            $safeDatabase = str_replace('`', '``', $database);
            $result = $db->query("SELECT COUNT(*) FROM `{$safeDatabase}`.ebook_ai_jobs WHERE status='processing'");
            return (int) $result->fetch_row()[0];
        } finally {
            if ($owned) $db->close();
        }
    }

    public function settingsAvailable(): bool
    {
        [$db, $owned] = $this->connection();
        try {
            return $this->tableExists($db, $this->databaseName($db), 'ebook_ai_settings');
        } finally {
            if ($owned) $db->close();
        }
    }

    public function settingValue(string $key): ?string
    {
        [$db, $owned] = $this->connection();
        try {
            $database = $this->databaseName($db);
            if (!$this->tableExists($db, $database, 'ebook_ai_settings')) return null;
            $safeDatabase = str_replace('`', '``', $database);
            $stmt = $db->prepare(
                "SELECT setting_value FROM `{$safeDatabase}`.ebook_ai_settings WHERE setting_key=? LIMIT 1"
            );
            $stmt->bind_param('s', $key);
            $stmt->execute();
            $row = $stmt->get_result()->fetch_assoc();
            $stmt->close();
            return isset($row['setting_value']) ? (string) $row['setting_value'] : null;
        } finally {
            if ($owned) $db->close();
        }
    }

    private function connection(): array
    {
        $host = trim((string) ($this->config['ebook_host'] ?? ''));
        if ($host === '') return [$this->musicDb, false];
        $name = trim((string) ($this->config['ebook_database'] ?? ''));
        $user = trim((string) ($this->config['ebook_user'] ?? ''));
        if ($name === '' || $user === '') throw new RuntimeException('Conexão de guarda do eBookLite incompleta.');
        $db = new mysqli(
            $host,
            $user,
            (string) ($this->config['ebook_password'] ?? ''),
            $name,
            (int) ($this->config['ebook_port'] ?? 3306)
        );
        if ($db->connect_errno) throw new RuntimeException('Conexão de guarda do eBookLite indisponível.');
        $db->set_charset('utf8mb4');
        return [$db, true];
    }

    private function databaseName(mysqli $db): string
    {
        $configured = trim((string) ($this->config['ebook_database'] ?? ''));
        if ($configured !== '') return $configured;
        $stmt = $db->prepare(
            "SELECT table_schema FROM information_schema.tables
             WHERE table_name='ebook_ai_jobs' ORDER BY table_schema"
        );
        $stmt->execute();
        $result = $stmt->get_result();
        $databases = [];
        while ($row = $result->fetch_assoc()) $databases[] = (string) $row['table_schema'];
        $stmt->close();
        if (count($databases) !== 1) throw new RuntimeException('Banco do eBookLite não identificado de forma unívoca.');
        return $databases[0];
    }

    private function tableExists(mysqli $db, string $database, string $table): bool
    {
        $stmt = $db->prepare(
            'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?'
        );
        $stmt->bind_param('ss', $database, $table);
        $stmt->execute();
        $exists = (int) $stmt->get_result()->fetch_row()[0] === 1;
        $stmt->close();
        return $exists;
    }
}
