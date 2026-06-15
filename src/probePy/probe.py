import subprocess, os, re
from shutil import which
from enum import StrEnum, auto
from src.probePy.exceptions import FFProbeError
class FORMAT_TYPE(StrEnum):
  JSON = auto()
  XML = auto()
class FFProbe:
  """An object wrapper thats wraps the ffprobe command-line."""
  def __init__(self, path:str,ffprobe_path:str=None,streams:bool=True,formats:bool=False, **kwargs):
    self.path = path
    if not os.path.isfile(path): raise FileNotFoundError
    self.ffprobe_path = ffprobe_path or which("ffprobe")
    if self.ffprobe_path is None:
      raise FileNotFoundError("A FFprobe binary was not found anywhere.")
    cmd = [self.ffprobe_path]
    if streams:
      cmd.append("-show_streams")
    if formats:
      cmd.append("-show_formats")
    for flag, value in kwargs.items():
      if value == True or value == 1:
        cmd.append(f"-{flag}")
      else:
        cmd.append(f"-{flag}")
        cmd.append(str(value))
    cmd.append(path)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stream = False
    self.streams = []
    self.video = []
    self.audio = []
    self.subtitle = []
    self.attachment = []
    for line in iter(proc.stdout.readline, b''):
      line = line.decode('utf-8')
      if '[STREAM]' in line:
        stream = True
        data_lines = []
      elif '[/STREAM]' in line and stream:
        stream = False
        self.streams.append(FFStream(data_lines))
      elif stream:
        data_lines.append(line)
    self.metadata = {}
    is_metadata = False
    stream_metadata_met = False
    for line in iter(proc.stderr.readline, b''):
      line = line.decode('utf-8')
      if 'Metadata:' in line and not stream_metadata_met:
        is_metadata = True
      elif 'Stream #' in line:
        is_metadata = False
        stream_metadata_met = True
      elif is_metadata:
        splits = line.split(',')
        for s in splits:
          m = re.search(r'(\w+)\s*:\s*(.*)$', s)
          if m: # Check ensuring regex actually found a match
            self.metadata[m.group(1)] = m.group(2).strip()
      if '[STREAM]' in line:
        stream = True
        data_lines = []
      elif '[/STREAM]' in line and stream:
        stream = False
        self.streams.append(FFStream(data_lines))
      elif stream:
        data_lines.append(line)
    proc.stdout.close()
    proc.stderr.close()
    proc.wait()
    for stream in self.streams:
      if stream.is_audio():
        self.audio.append(stream)
      elif stream.is_video():
        self.video.append(stream)
      elif stream.is_subtitle():
        self.subtitle.append(stream)
      elif stream.is_attachment():
        self.attachment.append(stream)
    self.audio = tuple(self.audio)
    self.video = tuple(self.video)
    self.subtitle = tuple(self.subtitle)
    self.attachment = tuple(self.attachment)
  
  def __repr__(self):
    return f"<FFprobe: metadata={self.metadata}, video={self.video}, audio={self.audio}, subtitle={self.subtitle}, attachment={self.attachment}>"
  

      
class FFStream:
  """An object wrapper of a stream from Probe metadata."""
  def __init__(self, data_lines):
        for line in data_lines:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                self.__dict__[key] = value
                
        # Calculate framerate safely
        if 'avg_frame_rate' in self.__dict__:
            try:
                num, den = map(int, self.__dict__['avg_frame_rate'].split('/'))
                self.__dict__['framerate'] = round(num / den)
            except (ValueError, ZeroDivisionError):
                self.__dict__['framerate'] = 0
        else:
            self.__dict__['framerate'] = None
  def __repr__(self):
        return f"<ProbeStream: codec={self.__dict__.get('codec_name', 'unknown')}, type={self.__dict__.get('codec_type', 'unknown')}>"
  def is_audio(self):
    """
    Checks if the stream is a audio type by codec.
    """
    return self.__dict__.get('codec_type', None) == 'audio'
  def is_video(self):
    """
    Checks if the stream is a video type by codec.
    """
    return self.__dict__.get('codec_type', None) == 'video'
  def is_subtitle(self):
    """
    Checks if the stream is a subtitle type by codec.
    """
    return self.__dict__.get('codec_type', None) == 'subtitle'
  def is_attachment(self):
    """
    Checks if the stream is an attachment type by codec.
    """
    return self.__dict__.get('codec_type', None) == 'attachment'
  def frame_size(self):
    """
    Returns the pixel frame size as an integer tuple (width, height) if the stream is a video stream.
    Returns None if it is not a video stream.
    """
    size = None
    if self.is_video():
      width = self.__dict__['width']
      height = self.__dict__['height']
      if width and height:
        try:
          size = (int(width), int(height))
        except ValueError:
          raise FFProbeError(f"Failed to convert non-integer size: {width} {height}")
      else:
        return None
      return size