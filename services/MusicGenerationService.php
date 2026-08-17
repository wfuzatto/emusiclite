<?php

interface MusicGenerationService
{
    public function backendName(): string;
    public function healthCheck(): array;
    public function generate(array $specification, string $destinationPath): array;
}
