<?php

class MusicPermanentException extends RuntimeException {}
class MusicTransientException extends RuntimeException {}
class MusicResourceBusyException extends MusicTransientException {}
