<?php

require_once __DIR__ . '/MusicGenerationService.php';
require_once __DIR__ . '/MusicExceptions.php';

class UnconfiguredMusicGenerationService implements MusicGenerationService
{
    public function backendName(): string { return 'unconfigured'; }
    public function healthCheck(): array { return ['online' => false, 'configured' => false, 'backend' => $this->backendName()]; }
    public function generate(array $specification, string $destinationPath): array
    {
        throw new MusicPermanentException('Nenhum gerador musical foi configurado após o inventário do servidor.');
    }
}
