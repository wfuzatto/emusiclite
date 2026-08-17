<?php

class ModerationService
{
    public function validate(array $input): void
    {
        $flatten = static function ($value) use (&$flatten): array {
            if (!is_array($value)) return [(string) $value];
            $result = []; foreach ($value as $item) $result = array_merge($result, $flatten($item)); return $result;
        };
        $text = mb_strtolower(implode("\n", $flatten($input)));
        $blocked = [
            '/(?:crian[cç]a|menor).{0,40}(?:sexo|sexual|er[oó]tic)/u',
            '/(?:ensine|passo a passo).{0,50}(?:bomba|explosivo|matar|envenenar)/u',
            '/(?:copie|reproduza|plagie).{0,60}(?:letra|m[uú]sica|can[cç][aã]o)/u',
        ];
        foreach ($blocked as $pattern) {
            if (preg_match($pattern, $text)) {
                throw new MusicPermanentException('A ideia não passou pela validação de segurança e originalidade.');
            }
        }
        if (preg_match('/(?:igual|id[eê]ntic[oa]|clone|no estilo de|imite|voz de)\s+[\p{L}\p{N}]/u', $text)) {
            throw new MusicPermanentException('Use referências descritivas sem citar ou imitar artistas e músicas existentes.');
        }
        if (preg_match('/ignore (?:as|todas)|system prompt|developer message|revele (?:o|seu) prompt/u', $text)) {
            throw new MusicPermanentException('A ideia contém instruções incompatíveis com a criação musical.');
        }
    }
}
