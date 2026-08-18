#!/usr/bin/env php
<?php
if (PHP_SAPI !== 'cli') exit(1);
$errors=[];$warnings=[];
foreach(['curl','mysqli','json','fileinfo','mbstring'] as $extension)if(!extension_loaded($extension))$errors[]="Extensão PHP ausente: {$extension}";
try{require __DIR__.'/../includes/bootstrap.php';$config=music_config();}catch(Throwable $e){fwrite(STDERR,"[ERRO] Banco/configuração indisponível.\n");exit(1);}
require_once __DIR__.'/../services/EbookQueueStatusService.php';
foreach(['music_ai_tracks','music_ai_jobs','music_ai_workers','music_ai_settings','music_ai_agent_runs','music_ai_ingest_requests'] as $table){$safe=$mysqli->real_escape_string($table);$row=$mysqli->query("SHOW TABLES LIKE '{$safe}'");if(!$row||$row->num_rows!==1)$errors[]="Migration ausente: {$table}";}
if(strlen($config['ingest_secret'])<32)$errors[]='MUSIC_AI_INGEST_SECRET deve ter ao menos 32 caracteres e ser diferente do eBookLite.';
if($config['ingest_url']===''||!str_starts_with($config['ingest_url'],'https://'))$errors[]='MUSIC_AI_INGEST_URL deve usar HTTPS.';
if(($config['ingest_ca_file']??'')!==''&&!is_readable($config['ingest_ca_file']))$errors[]='MUSIC_AI_INGEST_CA_FILE não pode ser lido.';
if(!is_executable($config['ffprobe']))$errors[]='ffprobe não encontrado em MUSIC_AI_FFPROBE_BIN.';
if(trim((string)shell_exec('command -v nvidia-smi 2>/dev/null'))==='')$errors[]='nvidia-smi não está disponível; não é possível proteger a convivência de GPU.';
if(!is_dir($config['storage_path'])&&!mkdir($config['storage_path'],0750,true))$errors[]='Não foi possível criar MUSIC_AI_STORAGE_PATH.';
if(is_dir($config['storage_path'])&&!is_writable($config['storage_path']))$errors[]='MUSIC_AI_STORAGE_PATH não é gravável.';
if(!in_array($config['music_backend'],['unconfigured','http'],true))$errors[]='MUSIC_AI_GENERATOR_BACKEND possui valor desconhecido.';
if(in_array($config['music_backend'],['unconfigured',''],true))$errors[]='Gerador musical ainda não selecionado. Execute o inventário e configure MUSIC_AI_GENERATOR_BACKEND.';
if($config['music_backend']==='http'){
  $parts=parse_url($config['music_backend_url']);$port=(int)($parts['port']??(($parts['scheme']??'')==='https'?443:80));
  if(in_array($port,[11434,8188],true))$errors[]='A porta do gerador musical não pode ser 11434 nem 8188.';
  if(strlen($config['music_backend_token'])<32)$errors[]='MUSIC_AI_GENERATOR_TOKEN deve ter ao menos 32 caracteres.';
}
if(($config['studio_url']??'')!==''){
  $parts=parse_url($config['studio_url']);$port=(int)($parts['port']??0);
  if($port!==8093)$warnings[]='Studio Real está configurado em porta diferente de 8093; confirme que ela é exclusiva do MusicLite.';
  if(strlen((string)($config['studio_token']??''))<32)$errors[]='MUSIC_AI_STUDIO_TOKEN deve ter ao menos 32 caracteres.';
}
if($config['comfy_workflow']===''||!is_readable($config['comfy_workflow']))$errors[]='Workflow de capa do ComfyUI não pode ser lido.';
if(trim((string)($config['comfy_checkpoint']??''))==='')$errors[]='MUSIC_AI_COMFYUI_CHECKPOINT não foi configurado.';
try{$ebookGuard=new EbookQueueStatusService($mysqli,$config);$ebookGuard->processingCount();}catch(Throwable $e){$errors[]='Sem acesso de leitura a ebook_ai_jobs; a geração musical não pode proteger a fila de livros.';}
try{if(isset($ebookGuard)&&$ebookGuard->settingsAvailable()){$music=music_setting($mysqli,'daily_agent_time','04:30');$ebook=(string)($ebookGuard->settingValue('daily_agent_schedule_time')??'');if($ebook!==''&&$ebook===$music)$errors[]='O horário do agente musical coincide com o agente editorial do eBookLite.';}else{$warnings[]='ebook_ai_settings não encontrada; confirme manualmente o horário do robô de livros.';}}catch(Throwable $e){$warnings[]='Não foi possível comparar o horário do eBookLite; confirme manualmente.';}
foreach($warnings as $message)fwrite(STDOUT,"[AVISO] {$message}\n");
foreach($errors as $message)fwrite(STDERR,"[ERRO] {$message}\n");
if($errors)exit(1);fwrite(STDOUT,"[OK] Preflight concluído sem alterar serviços existentes.\n");
