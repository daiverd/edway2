/* reformat.c -- Edway Audio Editor 
  * 
Copyright (c) 2009-2010, Charles E. Hallenbeck, Ph.D., chuckh@ftml.net
*
  *  This software is offered under the terms of the GNU General Public License
  *  as described in the file "COPYING" included with the software. Please read
  *  the terms and conditions of the GPL before using this software.
  * 
  */

#include "edway.h"
#include "protos.h"

extern char *configdir, *tempdir;
extern List *fhead, *ftail, *fnewest;
extern Session *head, *tail;
extern int wordsPerMinute;
extern char *rsfx[];
extern short r_table;
extern char *wsfx[];
extern short w_table;
extern short verbosity;
extern bool zaptarget, zapsource;
extern bool converting, smoothing, squeezing;
extern bool playing, timing;
extern int filtering;
extern bool speeding;
extern bool echoing;
extern int echoDelay;
extern char *speedFactor;
extern int lowerHertz;
extern int upperHertz;
extern int soundlevel;
extern char *ttsName;
extern bool helperstatus[];
extern double chancorr, chan1db, chan2db;
extern int autoReduce;
extern int autoRate;
extern int trvsr;
extern double autoCorr;
extern double autoDiff;
extern double oggqual;
extern double squeezeDB;
extern int squeezeKeep;
extern double smoothTime;
extern int smoothDrop;
extern double smoothDB;

bool
reformat (int channels0, int rate0, char *cname, char *ctype)
{
  List *fnext;
  List *ftemp;
  char buf[80];
  char *ch;
  short task = 0;
  int i;
  bool error = false;
  bool single = false;
  double total = 0;
  double seconds = 0;
  int minutes = 0;
  int hours = 0;
  StereoStats *g;

  if (!timing && !playing)
    {
      if (!cname && !ctype)
	{
	  puts ("No name  or type given for converting files.");
	  return (true);
	}
      if (cname && !ctype
	  && ((ch = strrchr (cname, '.'))
	      || (ch = strrchr (ftail->name, '.'))))
	ctype = xstrdup (ch + 1);
      if (cname && ctype && !strrchr (cname, '.'))
	{
	  sprintf (buf, "%s.%s", cname, ctype);
	  free (cname);
	  cname = xstrdup (buf);
	}
      if (cname && ctype && strrchr (cname, '.'))
	{
	  for (i = 0; i < w_table; i++)
	    if (!strcasecmp (wsfx[i], ctype))
	      break;
	  if (i != writable (cname))
	    {
	      printf ("Conflicting/unwritable suffix: %s and %s\n", cname,
		      ctype);
	      return (true);
	    }
	}

      for (i = 0; i < w_table; i++)
	if (!strcasecmp (wsfx[i], ctype))
	  break;
      if (i == w_table)
	{
	  printf ("I don't recognize the suffix \"%s\".\n", ctype);
	  return (true);
	}
    }				/* end of first converting steps */

  newSession (0);

  if (verbosity && fnewest)
    puts ("Using newest.");

  if (fhead == ftail)
    single = true;
  for (fnext = fhead; fnext != NULL; fnext = ftemp)
    {
      ftemp = fnext->next;
      if (fnewest == NULL || fnewest == fnext)
	{
	  int i;

	  if (++task && fhead && verbosity && !timing && !playing)
	    {
	      if (single)
		printf ("\nConverting %s\n", fnext->name);
	      else
		printf ("\n#%d, converting %s\n", task, fnext->name);
	    }

	  if (getAudio (fnext->name, fnext->sfx, cname))
	    {
	      error = true;
	      if (verbosity)
		printf ("decoding failed: %s \n", fnext->name);
	      continue;
	    }

	  if (timing)
	    {
	      double millisec;

	      seconds = 0;
	      minutes = hours = 0;
	      millisec = (1000.0 * tail->frames) / tail->samplerate;
	      total += millisec;
	      while (millisec >= MS_PER_HOUR)
		{
		  hours++;
		  millisec -= MS_PER_HOUR;
		}
	      while (millisec >= MS_PER_MINUTE)
		{
		  minutes++;
		  millisec -= MS_PER_MINUTE;
		}
	      seconds = millisec / 1000.0;
	      printf ("%s: ", tail->source);
	      if (hours)
		printf ("%dH", hours);
	      printf ("%dM%.03f, (%d * %d).\n", minutes, seconds,
		      tail->samplerate, tail->channels);
	      continue;
	    }

	  switch (filtering)
	    {
	    case bpf:
	      if (soxFilter (tail, lowerHertz, upperHertz))
		puts ("band pass filter failed.");
	      break;
	    case hpf:
	      if (soxFilter (tail, lowerHertz, 0))
		puts ("high pass filter failed.");
	      break;
	    case lpf:
	      if (soxFilter (tail, 0, upperHertz))
		puts ("low pass filter failed.");
	      break;
	    }

	  if (speeding)
	    {
	      double x = getFactor (tail, speedFactor);
	      soxFactor (tail, x);
	    }
	  if (echoing && soxEcho (tail, echoDelay))
	    puts ("sox echo failed.");

	  if (playing)
	    {
	      int key;

	      key = playfile (tail);
	      if (key == 'q')
		break;
	      if (key == 'p')
		{
		  if (fnext->prev)
		    ftemp = fnext->prev;
		  else
		    ftemp = fhead;
		}
	      continue;
	    }

	  i = writable (ctype);
	  setType (tail, ctype);
	  if (verbosity)
	    puts (tail->target);

	  if (tail->channels == 2 && channels0 == 5 && i != w_cdr
	      && i != w_aac && i != w_m4a)
	    {
	      g = correlate (tail, 1, tail->blocks);
	      if ((g->c1db - g->c2db) > autoDiff)
		setChannels (tail, 3);
	      else if ((g->c2db - g->c1db) > autoDiff)
		setChannels (tail, 4);
	      else if (channels0 == 1 || g->chancorr > autoCorr)
		setChannels (tail, 1);
	    }
	  if (channels0 == 5)
	    channels0 = 0;
	  sanitize (tail, soundlevel, true);
	  if (squeezing)
	    squeezit (tail, 1, tail->blocks, squeezeDB, squeezeKeep);
	  else if (verbosity)
	    printf ("Duration %s.\n", playtime (tail, 100));
	  if (smoothing)
	    smoothit (tail, 1, tail->blocks, smoothTime, smoothDrop,
		      smoothDB);
	  if (tail->frames < 1)
	    puts ("No data, skipping output.");
	  else if (strcasecmp (ctype, "null"))
	    {
	      if (putAudio (tail, channels0, rate0))
		printf ("Could not write %s\n", tail->target);
	    }
	  zapSession (tail);
	}
    }
  zaplist ();
  if (timing && task > 1)
    {
      seconds = 0;
      minutes = hours = 0;
      while (total >= MS_PER_HOUR)
	{
	  hours++;
	  total -= MS_PER_HOUR;
	}
      while (total >= MS_PER_MINUTE)
	{
	  minutes++;
	  total -= MS_PER_MINUTE;
	}
      seconds = total / 1000.0;
      printf ("Total time, %d files: ", task);
      if (hours)
	printf ("%dH", hours);
      printf ("%dM%.03f.\n", minutes, seconds);
    }

  return (error);
}				/* reformat */

const SF_INFO SFINFO_INITIALIZER = { 0 };

int
getAudio (char *name, int sfx, char *cname)
{
  int count;
  int i;
  short x;
  char buf[256];
  char bt;
  char *cp;
  struct stat fs;
  FILE *fin;
  SNDFILE *sndf;
  SF_INFO sfinfo = SFINFO_INITIALIZER;
  pid_t cpid;
  pid_t w;
  int status;
  char file1wav[256];
  char file2wav[256];
  FILE *rf;
  int rv;

  if (converting)
    zapSession (tail);
  if (!tail || tail->data)
    {
      newSession (0);
      if (verbosity)
	{
	  printf ("session #%d: ", tail->number);
	  fflush (stdout);
	}
    }

  stat (name, &fs);
  tail->size = fs.st_size;
  if (verbosity > 1)
    printf ("Suffix = %s.\n",
	    (char *) (sfx ? rsfx[sfx] : strrchr (name, '.')));

  sprintf (file1wav, "%s/f%da.wav", tempdir, (int) getpid ());
  sprintf (file2wav, "%s/f%db.wav", tempdir, (int) getpid ());
  switch (sfx)
    {
    case r_0:
      sfinfo.format = 0;
      sndf = sf_open (name, SFM_READ, &sfinfo);
      if (sf_error (sndf))
	return (1);
      tail->samplerate = sfinfo.samplerate;
      tail->channels = sfinfo.channels;
      if (timing)
	tail->frames = sfinfo.frames;
      else
	{
	  tail->data =
	    (short *) xmalloc (sizeof (short) * sfinfo.frames *
			       sfinfo.channels);
	  tail->frames = sf_readf_short (sndf, tail->data, sfinfo.frames);
	  if (sf_error (sndf))
	    return (1);
	}
      sf_close (sndf);
      break;
    case r_aac:
      if (helperstatus[faad])
	{
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "faad", "-q", "-d", "-o", file1wav,
		      name, (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}
	    }
	  break;
	}
      printf (FM12, "faad");
      return (1);
    case r_cdr:
      if (helperstatus[sox])
	{
	  {
	    cpid = fork ();
	    if (cpid == 0)
	      {
		rf = freopen ("/dev/null", "w", stdout);
		rf = freopen ("/dev/null", "w", stderr);
		execlp ("nice", "nice", "sox", "-q", "-tcdr", "-v0.7",
			name, "-t", "wav", file1wav, (char *) NULL);
	      }
	    else
	      {
		status = 0;
		while (true)
		  {
		    w = waitpid (cpid, &status, WNOHANG);
		    if (w == cpid && WIFEXITED (status))
		      break;
		  }		/* end while */
	      }			/* end else */
	  }
	  break;
	}
      printf (FM12, "SoX");
      return (1);
    case r_mp3:
      if (helperstatus[lame])
	{
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "lame", "--silent", "--decode", name,
		      file1wav, (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}		/* end while */
	    }			/* end else */
	  break;
	}
      printf (FM12, "lame");
      return (1);
    case r_ra:
    case r_rm:
    case r_3gp:
    case r_amr:
    case r_wv:
      if (helperstatus[ffmpeg])
	{
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "ffmpeg", "-i", name, "-f", "wav",
		      "-ar", "16000", "-ac", "1", file1wav, (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}		/* end while */
	    }			/* end else */
	  break;
	}
      printf (FM12, "ffmpeg");
      return (1);
    case r_ogg:
    case r_ogv:
      if (helperstatus[oggdec])
	{
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "oggdec", "-o",
		      file1wav, name, (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}		/* end while */
	    }			/* end else */
	  break;
	}
      printf (FM12, "oggdec");
      return (1);
    case r_spx:
      if (helperstatus[speexdec])
	{
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "speexdec", name, file1wav,
		      (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}		/* end while */
	    }			/* end else */
	  break;
	}
      printf (FM12, "speexdec");
      return (1);
    case r_trv:
      if (stat (name, &fs))
	{
	  printf ("Can't stat %s.\n", name);
	  return (1);
	}
      count = fs.st_size;
      tail->samplerate = 6000;
      tail->channels = 1;
      tail->frames = 0;
      tail->data = (short *) xcalloc (count * 2 + 1, sizeof (short));
      if (!(fin = fopen (name, "r")))
	{
	  printf ("Can't open %s for reading.\n", name);
	  return (1);
	}
      rv = fread (&bt, 1, 1, fin);
      while (!feof (fin))
	{
	  x = voxdecoder ((bt & 128), (bt & 64), (bt & 32), (bt & 16));
	  tail->data[tail->frames++] = x;
	  x = voxdecoder ((bt & 8), (bt & 4), (bt & 2), (bt & 1));
	  tail->data[tail->frames++] = x;
	  rv = fread (&bt, 1, 1, fin);
	}
      fclose (fin);
      if (verbosity > 2)
	printf ("count = %d.\n", count);
      break;
    case r_raw:
      tail->samplerate = sfinfo.samplerate = 22050;
      tail->channels = sfinfo.channels = 1;
      sfinfo.format = SF_FORMAT_RAW | SF_FORMAT_PCM_16;
      sndf = sf_open (name, SFM_READ, &sfinfo);
      if (sf_error (sndf))
	return (1);
      if (timing)
	tail->frames = sfinfo.frames;
      {
	tail->data =
	  (short *) xmalloc (sizeof (short) * sfinfo.frames *
			     sfinfo.channels);
	tail->frames = sf_readf_short (sndf, tail->data, sfinfo.frames);
	if (sf_error (sndf))
	  return (1);
      }
      sf_close (sndf);
      break;
    case r_txt:
      if (helperstatus[swift])
	{
	  if (wordsPerMinute)
	    {
	      sprintf (buf, "speech/rate=%d,audio/sampling-rate=16000",
		       wordsPerMinute);
	      cpid = fork ();
	      if (cpid == 0)
		{
		  rf = freopen ("/dev/null", "w", stdout);
		  rf = freopen ("/dev/null", "w", stderr);
		  execlp ("nice", "nice", "swift", "-p", buf, "-e", "utf-8",
			  "-f", name, "-o", file1wav, (char *) NULL);
		}
	      else
		{
		  status = 0;
		  while (true)
		    {
		      w = waitpid (cpid, &status, WNOHANG);
		      if (w == cpid && WIFEXITED (status))
			break;
		    }		/* end while */
		}		/* end else */
	    }
	  else
	    {
	      cpid = fork ();
	      if (cpid == 0)
		{
		  rf = freopen ("/dev/null", "w", stdout);
		  rf = freopen ("/dev/null", "w", stderr);
		  execlp ("nice", "nice", "swift", "-p",
			  "audio/sampling-rate=16000", "-e", "utf-8", "-f",
			  name, "-o", file1wav, (char *) NULL);
		}
	      else
		{
		  status = 0;
		  while (true)
		    {
		      w = waitpid (cpid, &status, WNOHANG);
		      if (w == cpid && WIFEXITED (status))
			break;
		    }		/* end while */
		}		/* end else */
	    }
	}
      else if (helperstatus[tts])
	{
	  if (strcmp (ttsName, "flite"))
	    {
	      sprintf (buf, "%d", wordsPerMinute);
	      cpid = fork ();
	      if (cpid == 0)
		{
		  rf = freopen ("/dev/null", "w", stdout);
		  rf = freopen ("/dev/null", "w", stderr);
		  execlp ("nice", "nice", ttsName, name, file1wav,
			  buf, (char *) NULL);
		}
	      else
		{
		  status = 0;
		  while (true)
		    {
		      w = waitpid (cpid, &status, WNOHANG);
		      if (w == cpid && WIFEXITED (status))
			break;
		    }		/* end while */
		}		/* end else */
	    }
	  else
	    {
	      cpid = fork ();
	      if (cpid == 0)
		{
		  rf = freopen ("/dev/null", "w", stdout);
		  rf = freopen ("/dev/null", "w", stderr);
		  execlp ("nice", "nice", "flite", name, file1wav,
			  (char *) NULL);
		}
	      else
		{
		  status = 0;
		  while (true)
		    {
		      w = waitpid (cpid, &status, WNOHANG);
		      if (w == cpid && WIFEXITED (status))
			break;
		    }		/* end while */
		}		/* end else */
	    }
	}
      else
	{
	  puts ("No TTS engine available.");
	  return (1);
	}
      break;
    case r_mid:
    case r_mod:
      if (helperstatus[timidity])
	{
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "timidity", "-Ow", "-o", file1wav, name,
		      (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}		/* end while */
	    }			/* end else */
	  break;
	}
      printf (FM12, "timidity");
      return (1);
    case r_asf:
    case r_avi:
    case r_flv:
    case r_m4a:
    case r_m4v:
    case r_mov:
    case r_mp4:
    case r_mpeg:
    case r_mpg:
    case r_swf:
    case r_wma:
    case r_wmv:
      if (helperstatus[mplayer])
	{
	  sprintf (buf, "pcm:file=%s", file1wav);
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "mplayer", "-vo", "null", "-ao", buf,
		      name, (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}		/* end while */
	    }			/* end else */
	  if (stat (file1wav, &fs) || fs.st_size < 46)
	    {
	      puts ("Aborting: decoding failed.");
	      exit (1);
	    }
	  break;
	}
      printf (FM12, "mplayer");
      return (1);
    case r_wav:
      if (helperstatus[sox])
	{
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "sox", "-v0.7", name, "-2", "-s",
		      file1wav, (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}
	    }
	  break;
	}
      printf (FM12, "SoX");
      return (1);
    default:
      printf ("Unknown file suffix %d.\n", sfx);
      return (1);
    }				/* switch */

  if (!stat (file1wav, &fs))
    {
      sfinfo.format = 0;
      sndf = sf_open (file1wav, SFM_READ, &sfinfo);
      if (sf_error (sndf))
	return (1);
      if ((sfinfo.format >> 16) == 1 && (sfinfo.format & 0xFFFF) != 2)
	{
	  sf_close (sndf);
	  if (verbosity > 1)
	    puts ("using signed 16 bit samples.");
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "sox", "-v0.8", file1wav, "-2", "-s",
		      file2wav, (char *) NULL);
	    }
	  else
	    {
	      status = 0;
	      while (true)
		{
		  w = waitpid (cpid, &status, WNOHANG);
		  if (w == cpid && WIFEXITED (status))
		    break;
		}		// end while
	    }			// end else
	  unlink (file1wav);
	  rename (file2wav, file1wav);
	  sfinfo.format = 0;
	  sndf = sf_open (file1wav, SFM_READ, &sfinfo);
	  if (sf_error (sndf))
	    return (1);
	}
      tail->samplerate = sfinfo.samplerate;
      tail->channels = sfinfo.channels;
      if (timing)
	tail->frames = sfinfo.frames;
      else
	{
	  tail->data =
	    (short *) xmalloc (sizeof (short) * sfinfo.frames *
			       sfinfo.channels);
	  tail->frames = sf_readf_short (sndf, tail->data, sfinfo.frames);
	  if (sf_error (sndf))
	    return (1);
	}
      sf_close (sndf);
      unlink (file1wav);
    }
  if (!timing && !tail->data)
    return (1);
  tail->blocksize =
    tail->frames < tail->samplerate * 2 ? tail->frames / 2 : tail->samplerate;
  tail->blocks = tail->frames / tail->blocksize;
  setBlocks (tail, 1000 * tail->blocksize / tail->samplerate, 0);
  tail->rsfx = tail->wsfx = sfx;
  tail->bstart = 0;
  tail->bstop = 1.0;
  tail->zfactor = ZX;
  tail->savedrate = tail->samplerate;
  tail->source = xstrdup (name);
  tail->target = xstrdup ("null.null");
  if (timing)
    return (0);
  if (playing || !converting)
    switch (tail->samplerate)
      {
      case 6000:
	setChannels (tail, 1);
	setSamplerate (tail, 8000);
	break;
      case 12000:
	setChannels (tail, 1);
	setSamplerate (tail, 16000);
	break;
      case 24000:
	setChannels (tail, 1);
	setSamplerate (tail, 32000);
	break;
      default:
	break;
      }
  if (cname)
    cp = cname;
  else
    {
      cp = strrchr (name, '/');
      if (cp == NULL)
	cp = name;
      else
	cp++;
    }
  strcpy (buf, checkname (cp));
  free (tail->target);
  tail->target = xstrdup (buf);
  if (writable (tail->target) == w_table)
    {
      strcpy ((cp = strrchr (tail->target, '.')), ".wav");
      tail->wsfx = w_wav;
    }
  if (autoReduce > 1 && tail->samplerate >= autoRate)
    setSamplerate (tail, tail->savedrate = tail->samplerate / 2);

  if (verbosity && !converting)
    puts (tail->target);
  tail->empty = true;
  count = tail->frames * tail->channels;
  for (i = 0; i < count; i++)
    if (abs (tail->data[i]) > 33)
      break;
  if (i < count)
    tail->empty = false;

  if (verbosity > 2)
    {
      printf ("Session #%d.\n", tail->number);
      printf ("Frames = %d.\n", tail->frames);
      printf ("Sample rate = %d.\n", tail->samplerate);
      printf ("Channels = %d.\n", tail->channels);
    }
  return 0;
}				/* getAudio */

int
putAudio (Session * this, int channels, int rate)
{
  struct stat fs;
  bool needhelp = false;
  int fmt;
  int frames;
  int i;
  short *data;
  char byte;
  char *ch;
  char buf[512];
  char filename[256];
  char cmd[256];
  int count;
  int format = 0;
  SNDFILE *sndf;
  SF_INFO sfinfo;
  FILE *fout;
  char file1wav[256];

  if (!this->target)
    {
      puts ("No filename given");
      return (1);
    }
  if (!(ch = strrchr (this->target, '.')))
    {
      puts ("Filename has no suffix");
      return (1);
    }
  if (writable (this->target) == w_table)
    {
      puts ("Not a writable file type.");
      return (1);
    }
  if (!rate)
    rate = this->savedrate;
  this->savedrate = rate;
  if (this->savedrate == 6000 && ((strstr (this->source, ".trv")
				   && !strstr (this->target, ".trv"))
				  || (strstr (this->source, ".trw")
				      && !strstr (this->target, ".trw"))))
    this->savedrate = rate = trvsr;
  if (!channels)
    channels = this->channels;
  if (!this->data)
    {
      puts ("No data to write");
      return (1);
    }

  if (this->bstart < 0 || this->bstop > 1.0 || this->bstart >= this->bstop)
    {
      printf ("Bad start or stop value: %0.03f, %0.03f\n", this->bstart,
	      this->bstop);
      return (1);
    }

  strcpy (filename, this->target);
  if (!converting)
    {
      if (!stat (filename, &fs))
	{
	  while (!(ch = readline ("Type O to overwrite, C to cancel: ")));
	  if (!strcasecmp (ch, "c"))
	    {
	      puts ("write aborted.");
	      return (0);
	    }
	  if (strcasecmp (ch, "o"))
	    {
	      strcpy (filename, newname (NULL, filename));
	    }
	  free (ch);
	}
    }
  else
    {
      sprintf (buf, "%s.%d", this->source, getpid ());
      if (zapsource && rename (this->source, buf))
	puts ("No permission to delete source file.");
      if (!zaptarget && !stat (filename, &fs)
	  && (!zapsource || strcasecmp (this->target, this->source)))
	strcpy (filename, newname (NULL, filename));
      if (stat (this->source, &fs))
	rename (buf, this->source);
    }
  unlink (file1wav);
  sprintf (file1wav, "%s/f%dc.wav", tempdir, (int) getpid ());
  switch (writable (this->target))
    {
    case w_aiff:
      if (rate == 0)
	setSamplerate (this, rate = 22254);
      if (this->channels == 2)
	setChannels (this, channels = 1);
      format = SF_FORMAT_AIFF | SF_FORMAT_PCM_S8;
      fmt = 2;
      break;
    case w_au:
      setSamplerate (this, this->savedrate = rate = 8000);
      setChannels (this, channels = 1);
      format = SF_FORMAT_AU | SF_FORMAT_ULAW;
      fmt = 2;
      break;
    case w_flac:
      if (helperstatus[flac])
	{
	  setSamplerate (this, rate);
	  if (channels && channels != this->channels)
	    setChannels (this, channels);
	  sprintf (cmd, FM03, filename, file1wav);
	  fmt = 1;
	  break;
	}
      printf (FM12, "flac");
      return (1);
    case w_wv:
      if (helperstatus[wavpack])
	{
	  setSamplerate (this, rate);
	  if (channels && channels != this->channels)
	    setChannels (this, channels);
	  sprintf (cmd, FM17, file1wav, filename);
	  fmt = 1;
	  break;
	}
      printf (FM12, "wavpack");
      return (1);
    case w_aac:
    case w_m4a:
      if (helperstatus[faac])
	{
	  setSamplerate (this, this->savedrate = rate = 44100);
	  setChannels (this, channels = 2);
	  sprintf (cmd, FM07, filename, file1wav);
	  fmt = 1;
	  break;
	}
      printf (FM12, "faac");
      return (1);
    case w_mp3:
      if (helperstatus[lame])
	{
	  setSamplerate (this, rate);
	  if (channels && channels != this->channels)
	    setChannels (this, channels);
	  sprintf (cmd, FM02, kbps (this), file1wav, filename);
	  fmt = 1;
	  break;
	}
      printf (FM12, "lame");
      return (1);
    case w_null:
      fmt = 12;
      break;
    case w_ogg:
      if (helperstatus[oggenc])
	{
	  setSamplerate (this, rate);
	  if (channels && channels != this->channels)
	    setChannels (this, channels);
	  sprintf (cmd, FM16, oggqual, filename, file1wav);
	  fmt = 1;
	  break;
	}
      printf (FM12, "oggenc");
      return (1);
    case w_3gp:
    case w_amr:
      if (helperstatus[ffmpeg])
	{
	  setSamplerate (this, rate);
	  if (channels && channels != this->channels)
	    setChannels (this, channels);
	  sprintf (cmd, FM04, file1wav, filename);
	  fmt = 1;
	  break;
	}
      printf (FM12, "ffmpeg");
      return (1);
    case w_rm:
      if (helperstatus[ffmpeg])
	{
	  setSamplerate (this, rate);
	  if (channels && channels != this->channels)
	    setChannels (this, channels);
	  sprintf (cmd, FM01, file1wav, kbps (this), filename);
	  fmt = 1;
	  break;
	}
      printf (FM12, "ffmpeg");
      return (1);
    case w_spx:
      if (helperstatus[speexenc])
	{
	  char bw[4];

	  if (rate < 16000)
	    {
	      rate = 8000;
	      strcpy (bw, "-n");
	    }
	  else if (rate < 32000)
	    {
	      rate = 16000;
	      strcpy (bw, "-w");
	    }
	  else
	    {
	      rate = 32000;
	      strcpy (bw, "-u");
	    }
	  setSamplerate (this, this->savedrate = rate);
	  if (channels && channels != this->channels)
	    setChannels (this, channels);
	  sprintf (cmd, FM09, bw, file1wav, filename);
	  fmt = 1;
	  break;
	}
      printf (FM12, "speexenc");
      return (1);
    case w_trv:
      setChannels (this, channels = 1);
      setSamplerate (this, this->savedrate = rate = 6000);
      fmt = 3;
      break;
    case w_trw:
      setChannels (this, channels = 1);
      setSamplerate (this, this->savedrate = rate = 6000);
      format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
      fmt = 2;
      break;
    case w_cdr:
      setSamplerate (this, this->savedrate = rate = 44100);
      setChannels (this, channels = 2);
      sprintf (cmd, FM11, file1wav, filename);
      fmt = 1;
      break;
    case w_gsm:
      setSamplerate (this, this->savedrate = rate = 8000);
      setChannels (this, channels = 1);
      format = 0X00040020;
      fmt = 2;
      break;
    case w_wav:
      setSamplerate (this, rate);
      if (channels && channels != this->channels)
	setChannels (this, channels);
      format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
      fmt = 2;
      break;
    default:
      puts ("Unsupported file type.");
      return (1);
    }				// switch

  frames = (this->bstop - this->bstart) * this->frames + 0.5;
  data =
    (short *) (this->data +
	       (int) (this->bstart * this->frames * this->channels + 0.5));


  switch (fmt)
    {
    case 1:
      sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
      sfinfo.channels = this->channels;
      sfinfo.samplerate = this->savedrate;
      sndf = sf_open (file1wav, SFM_WRITE, &sfinfo);
      if (sf_error (sndf))
	return (1);
      count = sf_writef_short (sndf, data, frames);
      if (sf_error (sndf))
	return (1);
      sf_close (sndf);
      needhelp = true;
      break;
    case 2:			/* wav, trw */
      sfinfo.format = format;
      sfinfo.channels = this->channels;
      sfinfo.samplerate = this->savedrate;
      sndf = sf_open (filename, SFM_WRITE, &sfinfo);
      if (sf_error (sndf))
	return (1);
      count = sf_writef_short (sndf, (short *) data, frames);
      if (sf_error (sndf))
	return (1);
      sf_close (sndf);
      break;
    case 3:
      if (!(fout = fopen (filename, "w")))
	return (1);
      byte = 128;		// magic number
      for (i = 0; i < 24; i++)
	fwrite (&byte, 1, 1, fout);
      for (i = 0; i < frames; i += 2)
	{
	  byte = voxencoder (data[i], data[i + 1]);
	  fwrite (&byte, 1, 1, fout);
	}
      fclose (fout);
      break;
    default:
      puts ("Skipping output.");
      return (0);
    }				// switch
  if (needhelp)			// spawn faac, speex, oggenc, flac, or lame
    {
      if (verbosity > 2)
	puts (cmd);
      if (system (cmd))
	{
	  puts ("Conversion failed. No idea why.");
	  return (1);
	}
      unlink (file1wav);
    }				// end of needhelp
  if (verbosity)
    {
      printf ("Saved");
      if (!converting)
	printf (" %s", filename);
      stat (filename, &fs);
      if (fs.st_size > MB)
	printf (", %.1fM", ((double) fs.st_size) / MB);
      else if (fs.st_size > KB)
	printf (", %.1fK", ((double) fs.st_size) / KB);
      else
	printf (", %dB", (int) fs.st_size);
      if (this->size > 10000)
	printf (" or %ld%% of original size.",
		fs.st_size / (this->size / 100));
      puts ("");
    }
  sprintf (buf, "%s.%d", filename, getpid ());
  rename (filename, buf);
  if (stat (this->source, &fs) && converting)
    puts ("source overwritten.");
  else if (zapsource)
    {
      if (unlink (this->source))
	puts ("Unable to delete source.");
      else
	puts ("Source deleted.");
    }
  rename (buf, filename);
  return (0);
}				/* putAudio */
