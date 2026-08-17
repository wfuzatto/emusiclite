<?php

if (!function_exists('music_env')) {
    function music_env(string $key, $default = null)
    {
        $value = getenv($key);
        return $value === false || $value === '' ? $default : $value;
    }

    function music_env_bool(string $key, bool $default = false): bool
    {
        $value = music_env($key, null);
        return $value === null ? $default : filter_var($value, FILTER_VALIDATE_BOOLEAN);
    }
}

return [
    'enabled' => music_env_bool('MUSIC_AI_ENABLED', true),
    'timezone' => (string) music_env('MUSIC_AI_TIMEZONE', 'America/Sao_Paulo'),
    'subject_key' => (string) music_env('MUSIC_AUTH_SUBJECT_KEY', ''),
    'admin_user_ids' => array_values(array_filter(array_map('intval', explode(',', (string) music_env('MUSIC_AI_ADMIN_USER_IDS', ''))))),
    'ollama_url' => rtrim((string) music_env('MUSIC_AI_OLLAMA_URL', 'http://127.0.0.1:11434'), '/'),
    'ollama_model' => (string) music_env('MUSIC_AI_OLLAMA_MODEL', ''),
    'ollama_keep_alive' => (string) music_env('MUSIC_AI_OLLAMA_KEEP_ALIVE', '0'),
    'ollama_timeout' => max(15, (int) music_env('MUSIC_AI_OLLAMA_TIMEOUT', 300)),
    'music_backend' => strtolower((string) music_env('MUSIC_AI_GENERATOR_BACKEND', 'unconfigured')),
    'music_backend_url' => rtrim((string) music_env('MUSIC_AI_GENERATOR_URL', ''), '/'),
    'music_backend_token' => (string) music_env('MUSIC_AI_GENERATOR_TOKEN', ''),
    'music_backend_timeout' => max(60, (int) music_env('MUSIC_AI_GENERATOR_TIMEOUT', 1800)),
    'comfy_url' => rtrim((string) music_env('MUSIC_AI_COMFYUI_URL', 'http://127.0.0.1:8188'), '/'),
    'comfy_workflow' => (string) music_env('MUSIC_AI_COMFYUI_WORKFLOW', ''),
    'comfy_checkpoint' => (string) music_env('MUSIC_AI_COMFYUI_CHECKPOINT', ''),
    'comfy_timeout' => max(60, (int) music_env('MUSIC_AI_COMFYUI_TIMEOUT', 900)),
    'storage_path' => rtrim((string) music_env('MUSIC_AI_STORAGE_PATH', '/var/lib/musiclite'), '/'),
    'public_media_path' => rtrim((string) music_env('MUSIC_AI_PUBLIC_MEDIA_PATH', dirname(__DIR__) . '/storage/music-ai'), '/'),
    'ingest_url' => rtrim((string) music_env('MUSIC_AI_INGEST_URL', ''), '/'),
    'ingest_secret' => (string) music_env('MUSIC_AI_INGEST_SECRET', ''),
    'ingest_ca_file' => (string) music_env('MUSIC_AI_INGEST_CA_FILE', ''),
    'ingest_max_skew' => max(30, min(900, (int) music_env('MUSIC_AI_INGEST_MAX_SKEW', 300))),
    'trust_proxy_https' => music_env_bool('MUSIC_AI_TRUST_PROXY_HTTPS', false),
    'max_audio_mb' => max(10, (int) music_env('MUSIC_AI_MAX_AUDIO_MB', 100)),
    'max_cover_mb' => max(2, (int) music_env('MUSIC_AI_MAX_COVER_MB', 15)),
    'ffprobe' => (string) music_env(
        'MUSIC_AI_FFPROBE_BIN',
        is_executable('/usr/bin/ffprobe') ? '/usr/bin/ffprobe' : '/usr/local/bin/ffprobe'
    ),
    'min_free_vram_mb' => max(512, (int) music_env('MUSIC_AI_MIN_FREE_VRAM_MB', 5200)),
    'ebook_host' => (string) music_env('MUSIC_AI_EBOOK_DB_HOST', ''),
    'ebook_port' => (int) music_env('MUSIC_AI_EBOOK_DB_PORT', 3306),
    'ebook_database' => (string) music_env('MUSIC_AI_EBOOK_DB_NAME', ''),
    'ebook_user' => (string) music_env('MUSIC_AI_EBOOK_DB_USER', ''),
    'ebook_password' => (string) music_env('MUSIC_AI_EBOOK_DB_PASSWORD', ''),
    'worker_timeout_minutes' => max(5, (int) music_env('MUSIC_AI_WORKER_TIMEOUT_MINUTES', 20)),
];
