<?php
require __DIR__.'/../../includes/bootstrap.php';$user=music_current_user($mysqli,true);$id=(int)($_GET['id']??0);$uid=(int)$user['id'];
$stmt=$mysqli->prepare("SELECT id,title,description,genre,subgenre,mood,theme,language,composition_type,desired_duration_seconds,bpm,voice_type,instruments,status,current_stage,progress_percent,is_published,published_at,audio_media_id,cover_media_id,last_error,created_at,updated_at FROM music_ai_tracks WHERE id=? AND owner_user_id=? AND status<>'DELETED' LIMIT 1");$stmt->bind_param('ii',$id,$uid);$stmt->execute();$track=$stmt->get_result()->fetch_assoc();$stmt->close();if(!$track)music_json(['ok'=>false,'message'=>'Música não encontrada.'],404);
$stmt=$mysqli->prepare("SELECT status,attempts,next_attempt_at,error_code FROM music_ai_jobs WHERE track_id=? AND status IN ('PENDING','PROCESSING','FAILED') ORDER BY id DESC LIMIT 1");$stmt->bind_param('i',$id);$stmt->execute();$job=$stmt->get_result()->fetch_assoc();$stmt->close();
if($job){unset($job['error_code']);}$track['last_error']=$track['last_error']?'A criação precisa de atenção. Consulte o estado e tente retomar.':null;
music_json(['ok'=>true,'track'=>$track,'job'=>$job]);
