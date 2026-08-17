<?php

require_once __DIR__ . '/UnconfiguredMusicGenerationService.php';
require_once __DIR__ . '/HttpMusicGenerationService.php';

class MusicGenerationFactory
{
    public static function create(array $config): MusicGenerationService
    {
        return match ($config['music_backend']) {
            'http' => new HttpMusicGenerationService($config),
            default => new UnconfiguredMusicGenerationService(),
        };
    }
}
