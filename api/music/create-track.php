<?php

require __DIR__ . '/../../includes/bootstrap.php';
require_once __DIR__ . '/../../services/TrackService.php';
music_api_post(); $user=music_current_user($mysqli,true); music_api_csrf(); music_rate_limit($mysqli,(int)$user['id'],'create_track',8);
if(music_setting($mysqli,'ai_enabled','1')!=='1')music_json(['ok'=>false,'message'=>'A criação musical está temporariamente indisponível.'],503);
$input=[];foreach(['genre','subgenre','mood','theme','language','composition_type','voice_type','instruments','descriptive_references','original_idea','desired_duration_seconds','bpm','generation_model'] as $key)$input[$key]=is_string($_POST[$key]??null)?trim($_POST[$key]):($_POST[$key]??null);
$allowedTypes=['INSTRUMENTAL','VOCAL'];$allowedLanguages=['Português','Inglês','Espanhol','Francês','Italiano','Alemão','Sem idioma'];$allowedModels=['turbo','shift1','shift3','xl_sft','stable_audio'];
if(!in_array($input['composition_type'],$allowedTypes,true)||!in_array($input['language'],$allowedLanguages,true))music_json(['ok'=>false,'message'=>'Revise o tipo de composição e o idioma.'],422);
if(!in_array((string)$input['generation_model'],$allowedModels,true))music_json(['ok'=>false,'message'=>'Selecione um modelo de geração válido.'],422);
if($input['generation_model']==='stable_audio'&&$input['composition_type']!=='INSTRUMENTAL')music_json(['ok'=>false,'message'=>'Stable Audio Open está habilitado apenas para samples instrumentais.'],422);
if(mb_strlen((string)$input['original_idea'])<20||mb_strlen((string)$input['original_idea'])>8000)music_json(['ok'=>false,'message'=>'Descreva a ideia usando entre 20 e 8.000 caracteres.'],422);
foreach(['genre'=>120,'subgenre'=>120,'mood'=>120,'theme'=>255,'voice_type'=>120,'instruments'=>3000,'descriptive_references'=>3000] as $key=>$limit)if(mb_strlen((string)$input[$key])>$limit)music_json(['ok'=>false,'message'=>'Um dos campos ultrapassa o limite permitido.'],422);
$duration=(int)$input['desired_duration_seconds'];if($duration<30||$duration>180)music_json(['ok'=>false,'message'=>'O gerador musical atual suporta duração entre 30 segundos e 3 minutos.'],422);
if(in_array($input['generation_model'],['xl_sft','stable_audio'],true)&&$duration>30)music_json(['ok'=>false,'message'=>'Os modos experimentais XL SFT 4B e Stable Audio estão limitados a samples de 30 segundos.'],422);
if($input['bpm']!==''&&$input['bpm']!==null&&((int)$input['bpm']<40||(int)$input['bpm']>240))music_json(['ok'=>false,'message'=>'O BPM deve ficar entre 40 e 240.'],422);
$uid=(int)$user['id'];$max=(int)music_setting($mysqli,'max_active_tracks','3');$stmt=$mysqli->prepare("SELECT COUNT(*) total FROM music_ai_tracks WHERE owner_user_id=? AND status IN ('PLANNING','QUEUED','GENERATING')");$stmt->bind_param('i',$uid);$stmt->execute();$active=(int)$stmt->get_result()->fetch_assoc()['total'];$stmt->close();if($active>=$max)music_json(['ok'=>false,'message'=>'Conclua ou exclua um projeto em andamento antes de criar outro.'],429);
$daily=(int)music_setting($mysqli,'max_generations_per_day','100');$stmt=$mysqli->prepare("SELECT COUNT(*) total FROM music_ai_tracks WHERE owner_user_id=? AND source='USER' AND created_at>=CURDATE()");$stmt->bind_param('i',$uid);$stmt->execute();$today=(int)$stmt->get_result()->fetch_assoc()['total'];$stmt->close();if($today>=$daily)music_json(['ok'=>false,'message'=>'Seu limite diário de criações foi atingido.'],429);
try{$trackId=(new TrackService($mysqli))->create($uid,$input);music_json(['ok'=>true,'track_id'=>$trackId,'message'=>'Projeto criado e colocado na fila.'],201);}catch(MusicPermanentException|InvalidArgumentException $e){music_json(['ok'=>false,'message'=>$e->getMessage()],422);}catch(Throwable $e){music_json(['ok'=>false,'message'=>'Não foi possível criar o projeto agora.'],500);}
