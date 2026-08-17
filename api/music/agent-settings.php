<?php
require __DIR__.'/../../includes/bootstrap.php';music_api_post();music_require_admin($mysqli);music_api_csrf();$values=$_POST['settings']??[];if(!is_array($values))music_json(['ok'=>false,'message'=>'Configuração inválida.'],422);
$allowed=['daily_agent_enabled','daily_agent_time','daily_agent_duration_seconds','daily_agent_genres','daily_agent_composition_types','daily_agent_auto_publish'];$clean=[];
foreach($allowed as $key){if(!array_key_exists($key,$values))continue;$clean[$key]=trim((string)$values[$key]);}
foreach(['daily_agent_enabled','daily_agent_auto_publish'] as $key)if(isset($clean[$key])&&!in_array($clean[$key],['0','1'],true))music_json(['ok'=>false,'message'=>'Configuração inválida.'],422);
if(isset($clean['daily_agent_time'])&&!preg_match('/^(?:[01]\d|2[0-3]):[0-5]\d$/',$clean['daily_agent_time']))music_json(['ok'=>false,'message'=>'Horário inválido.'],422);
if(isset($clean['daily_agent_duration_seconds'])&&((int)$clean['daily_agent_duration_seconds']<30||(int)$clean['daily_agent_duration_seconds']>600))music_json(['ok'=>false,'message'=>'Duração inválida.'],422);
if(isset($clean['daily_agent_genres'])&&(mb_strlen($clean['daily_agent_genres'])<2||mb_strlen($clean['daily_agent_genres'])>1000))music_json(['ok'=>false,'message'=>'Informe ao menos um gênero válido.'],422);
if(isset($clean['daily_agent_composition_types'])){$types=array_map('trim',explode(',',$clean['daily_agent_composition_types']));if(!$types||array_diff($types,['INSTRUMENTAL','VOCAL']))music_json(['ok'=>false,'message'=>'Tipos de composição inválidos.'],422);}
$stmt=$mysqli->prepare("INSERT INTO music_ai_settings(setting_key,setting_value,description) VALUES(?,?,'Configuração editorial') ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)");
foreach($clean as $key=>$value){$stmt->bind_param('ss',$key,$value);$stmt->execute();}$stmt->close();music_json(['ok'=>true,'message'=>'Preferências editoriais salvas.']);
