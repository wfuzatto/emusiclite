<?php
require __DIR__.'/../../includes/bootstrap.php';require_once __DIR__.'/../../services/TrackService.php';music_api_post();$user=music_current_user($mysqli,true);music_api_csrf();$id=(int)($_POST['track_id']??0);music_require_owned_track($mysqli,$id,(int)$user['id']);
try{(new TrackService($mysqli))->publish($id,(int)$user['id']);music_json(['ok'=>true,'message'=>'Música publicada no catálogo.']);}catch(MusicPermanentException $e){music_json(['ok'=>false,'message'=>$e->getMessage()],409);}
