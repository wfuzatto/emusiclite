# IA musical no eMusic Lite

## Arquitetura implementada

O PHP da Locaweb autentica o cliente, mantém os projetos, a fila MySQL, o catálogo e os arquivos. Uma requisição web apenas cria registros em `music_ai_tracks` e `music_ai_jobs`; ela nunca gera áudio ou capa.

O daemon do Ubuntu lê a fila durável, usa o Ollama existente somente por API, chama um `MusicGenerationService` configurável, valida o áudio com `ffprobe`, chama o ComfyUI existente somente por API e envia áudio/capa à Locaweb por HTTPS multipart assinado. Todos os componentes novos usam nomes `music_ai_*`, variáveis `MUSIC_*`/`MUSIC_AI_*`, usuário `musiclite` e diretórios exclusivos.

## Checkpoints e retomada

Cada projeto registra: projeto, plano, letra, prompt musical, áudio gerado, áudio validado, áudio recebido, capa gerada, capa recebida e publicação. Arquivos intermediários ficam em `/var/lib/musiclite/tracks/<id>`. A operation key torna o job idempotente; a chave `daily:AAAA-MM-DD` torna o agente diário idempotente.

O worker recupera jobs cujo dono parou ou cujo heartbeat venceu. Falhas transitórias têm três tentativas rápidas (5, 15 e 30 segundos), depois 1, 2, 4, 8, 16 e no máximo 30 minutos. Espera por GPU/eBookLite não consome tentativa. Falha definitiva é reservada a moderação, validação de arquivo e configuração não recuperável.

## Contrato do gerador musical

O backend é escolhido por `MUSIC_AI_GENERATOR_BACKEND`. O valor inicial obrigatório é `unconfigured`; nenhuma tecnologia ou porta deve ser escolhida antes do inventário.

O adaptador `http` espera:

- `GET /health`, com HTTP 2xx;
- `POST /generate`, JSON com prompt, letra, instrumental/voz, gênero, subgênero, clima, idioma, duração, BPM, voz e instrumentos;
- resposta JSON `{"audio_url":"https://...","job_id":"..."}`;
- o download deve produzir áudio reconhecido pelo `ffprobe`.

O token opcional usa `Authorization: Bearer`. A porta deve ser exclusiva e nunca 11434 ou 8188.

## Privacidade e segurança

O CPF é transformado em identificador HMAC antes de chegar às tabelas da IA. CPF, sessão e dados contratuais não entram em prompts. Planos, letras em rascunho, referências e prompts internos não são expostos no catálogo. Mídia privada exige sessão e propriedade.

A ingestão usa HTTPS, HMAC-SHA256, timestamp curto, UUID, SHA-256 do arquivo e tabela antirreplay. O arquivo é recebido em multipart, revalidado na Locaweb, gravado como `.part` e concluído por `rename`. O segredo deve ser aleatório, ter no mínimo 32 caracteres e ser diferente de qualquer segredo do eBookLite.

## Interface ComfyUI

O serviço usa `client_id` com prefixo `musiclite-`, consulta `/queue`, só envia workflow quando a fila existente está livre e nunca chama `/free`. O JSON indicado por `MUSIC_AI_COMFYUI_WORKFLOW` deve ser exportado em formato API e conter `{{PROMPT}}` no campo de prompt. Nenhum checkpoint, plugin ou modelo é instalado automaticamente.
