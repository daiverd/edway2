/* main.c -- Edway Audio Editor 
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

extern char *optarg;
extern int optind, opterr, optopt;
#define _GNU_SOURCE
#include <getopt.h>

 /* miscellaneous */
static struct termios savettybuf;
short verbosity = 1;
static bool isInteractive;
bool converting = false;
bool playing = false;
bool smoothing = false;
bool squeezing = false;
bool timing = false;
bool public = true;
bool quietflag = false;
bool zapsource = false;
bool zaptarget = false;
int filtering = unf;
bool speeding = false;
bool echoing = false;
int echoDelay = 100;
char *soxVersion = NULL;
char *xpfEffect = NULL;
char *speedFactor = NULL;
bool ignore = false;
int soundlevel = 3277;
int wordsPerMinute = 0;
/* These appear in the configuration file */
int autoReduce = 0;
int autoRate = 32000;
int trvsr = 8000;
double autoCorr = 0.98;
double autoDiff = 24.0;
double oggqual = OGGQUAL;
bool descending = false;
bool newest = false;
char *playDevice = NULL;
char *captureDevice = NULL;
double squeezeDB = 48;
int squeezeKeep = 1;
double smoothTime = 2.0;
int smoothDrop = 1;
double smoothDB = 3.0;
int lowerHertz = 300;
int upperHertz = 3000;

char *configdir = NULL;
char *backuptext = NULL;
char *backupwave = NULL;
char *tempdir = NULL;
char *tempfile = NULL;
char *ttsName = NULL;
Lines *c_head = NULL, *c_tail = NULL;
List *fhead = NULL, *ftail = NULL, *fnewest = NULL;
Session *head = NULL, *tail = NULL;

/* readable file types by suffix */
char *rsfx[] =
  { "+", "3gp", "aac", "amr", "asf", "avi", "cdr", "flv", "m4a", "m4v", "mid",
  "mod", "mov", "mp3", "mp4", "mpeg", "mpg", "ogg", "ogv", "ra", "raw", "rm",
  "spx", "swf", "txt", "trv", "wav", "wma", "wmv", "wv"
};

short r_table = sizeof (rsfx) / sizeof (char *);

/* writable file types by suffix */
char *wsfx[] =
  { "3gp", "aac", "aiff", "amr", "au", "cdr", "flac", "gsm", "m4a", "mp3",
  "null", "ogg", "rm", "spx", "trv", "trw", "wav", "wv"
};

short w_table = sizeof (wsfx) / sizeof (char *);

/* helper programs */
char *helpername[] =
  { "arecord", "faac", "faad", "flac", "ffmpeg", "lame", "mplayer", "oggdec",
  "oggenc",
  "sox",
  "speexdec", "speexenc", "swift", "timidity", "tts", "wavpack"
};

short h_table = sizeof (helpername) / sizeof (char *);
bool helperstatus[sizeof (helpername) / sizeof (char *)];
char *cmd[] =
  { "!", "/", "=", "?", "??", "b", "bpf", "cap", "cs", "d", "db", "e", "ek",
  "f", "fi", "fo", "ft", "g", "gen", "h", "hg", "hpf", "j", "k", "l", "lpf",
  "m", "ms", "mx", "nb", "nc", "oq", "p", "pub", "q", "qt", "r", "rb",
  "sl", "sm", "sq", "sr", "t", "u", "uv", "v", "vs", "w", "z", "zap", "-a",
  "-b", "-c", "-d", "-e", "-f", "-h", "-i", "-l", "-n", "-o", "-p", "-q",
  "-r", "-t", "-V", "-v", "-w", "-z"
};

short c_table = sizeof (cmd) / sizeof (char *);


static void
ttySaveSettings (void)
{
  isInteractive = isatty (0);
  if (isInteractive)
    {
      if (tcgetattr (0, &savettybuf))
	fputs ("Cannot save tty settings.", stderr);
    }
}				/* ttySaveSettings */

int
getch (void)
{
  struct termios buf = savettybuf;

  char c = 5;
  int rv;

  fflush (stdout);
  cfmakeraw (&buf);
  buf.c_cc[VMIN] = 0;
  buf.c_cc[VTIME] = 0;
  tcsetattr (0, TCSANOW, &buf);
  rv = read (0, &c, 1);
  if (isInteractive)
    tcsetattr (0, TCSANOW, &savettybuf);
  return (c);
}				/* getch */

void *
xmalloc (size_t numbytes)
{
  void *mem = malloc (numbytes);
  if (mem == NULL)
    {
      fprintf (stderr, "Out of memory!\n");
      exit (1);
    }
  return mem;
}

/*
char *
xstrdup (const char *s)
{
  char *mem = strdup (const char *s);
  if (mem == NULL)
    {
      fprintf (stderr, "Out of memory!\n");
      exit (1);
    }
  return mem;
}
*/

char *
xstrdup (const char *src)
{
  char *newstr = strdup (src);
  if (newstr == NULL)
    {
      fprintf (stderr, "Out of memory!\n");
      exit (1);
    }
  return newstr;
}

void *
x_realloc (void *mem, size_t size)
{
  void *newmem = realloc (mem, size);
  if (newmem == NULL)
    {
      fprintf (stderr, "Out of memory!\n");
      exit (1);
    }
  return newmem;
}

void *
xcalloc (size_t nmemb, size_t size)
{
  void *newmem = calloc (nmemb, size);
  if (newmem == NULL)
    {
      fprintf (stderr, "Out of memory!\n");
      exit (1);
    }
  return newmem;
}

void
catchsig (int n)
{
  unlink ("/var/tmp/quiet.edway");
  unlink (backuptext);
  unlink (backupwave);
  exit (0);
}

int
main (int argc, char **argv)
{
  int i;
  int channels = 0;
  int rate = 0;
  char *newtype = NULL;
  char *newname = NULL;
  bool error = false;
  List *fnext;
  struct option long_option[] = {
    {"auto", 0, NULL, 'a'},
    {"batch", 1, NULL, 'b'},
    {"convert", 1, NULL, 'c'},
    {"descend", 0, NULL, 'd'},
    {"engine", 1, NULL, 'e'},
    {"flag", 0, NULL, 'f'},
    {"help", 0, NULL, 'h'},
    {"ignore", 0, NULL, 'i'},
    {"level", 1, NULL, 'l'},
    {"newest", 0, NULL, 'n'},
    {"other", 1, NULL, 'o'},
    {"play", 0, NULL, 'p'},
    {"quiet", 0, NULL, 'q'},
    {"rate", 1, NULL, 'r'},
    {"timing", 0, NULL, 't'},
    {"verbose", 0, NULL, 'v'},
    {"version", 0, NULL, 'V'},
    {"wpm", 1, NULL, 'w'},
    {"zap", 1, NULL, 'z'},
    {NULL, 0, NULL, 0}
  };

  ttySaveSettings ();
  getconfig ();
  signal (SIGINT, catchsig);
  if (autoReduce == 1 || autoReduce == 3)
    channels = 5;

  while (true)
    {
      int c;
      char *ch;
      if ((c =
	   getopt_long (argc, argv,
			"a:b:c:de:fhil:no:pqr:tvVw:z:",
			long_option, NULL)) < 0)
	break;
      switch (c)
	{
	case 'a':		/* stereo to mono and rate change */
	  i = atoi (optarg);
	  if (i >= 0 && i <= 3)
	    autoReduce = i;
	  if (i == 0 || i == 2)
	    break;
	  if (!channels)
	    channels = 5;
	  else if (channels == 5)
	    channels = 0;
	  break;
	case 'b':		/* batch: squeezing, smoothing, public */
	  i = atoi (optarg);
	  squeezing = smoothing = public = false;
	  if (i > 0)
	    squeezing = true;
	  if (i > 1)
	    smoothing = true;
	  if (i > 2)
	    public = true;
	  break;
	case 'c':		/* conversion formats */
	  converting = true;
	  if (strrchr (optarg, '.'))
	    {
	      newname = xstrdup (optarg);
	      if (strlen ((ch = strrchr (newname, '.'))) > 1)
		newtype = xstrdup (ch + 1);
	      *ch = 0;
	    }
	  else
	    newtype = xstrdup (optarg);
	  break;
	case 'd':		/* descend into directories */
	  descending = (descending ? false : true);
	  break;
	case 'e':		/* extra tts helper */
	  ttsName = xstrdup (optarg);
	  if ((helperstatus[tts] = lookfor (ttsName)))
	    helperstatus[swift] = false;
	  else
	    printf ("%s not found.\n", ttsName);
	  break;
	case 'f':		/* set the quietflag */
	  quietflag = (quietflag ? false : true);
	  break;
	case 'h':		/* show initial help and exit */
	  if (converting)
	    break;
	  show1help ("dh-help");
	  exit (0);
	case 'i':		/* ignore backups and histories */
	  ignore = (ignore ? false : true);
	  break;
	case 'l':		/* set soundlevel */
	  i = atoi (optarg);
	  if (i < 33 || i > 16384)
	    printf ("Soundlevel %d must be between 33 and 16384.", i);
	  else
	    soundlevel = i;
	  break;
	case 'n':		/* newest */
	  newest = (newest ? false : true);
	  break;
	case 'o':		/* other parameters */
	  if (getOthers (optarg))
	    printf ("error: --other %s\n", optarg);
	  break;
	case 'p':		/* play */
	  if (!converting)
	    converting = playing = true;
	  break;
	case 'q':		/* be more quiet */
	  if (verbosity)
	    verbosity--;
	  break;
	case 'r':		/* samplerate */
	  i = atoi (optarg);
	  i = realrate (i);
	  if (i && i < 5000)
	    {
	      fprintf (stderr, "Unrecognized rate %d, aborting.\n", i);
	      exit (1);
	    }
	  rate = i;
	  if (tolower (optarg[strlen (optarg) - 1]) == 'm')
	    channels = 1;
	  else if (tolower (optarg[strlen (optarg) - 1]) == 's')
	    channels = 2;
	  break;
	case 't':		/* report time and stats */
	  if (!converting)
	    converting = timing = true;
	  break;
	case 'v':		/* be more verbose */
	  verbosity++;
	  break;
	case 'V':		/* show program version and exit */
	  printf ("Edway version %s.%s\n", VERSION, REVISION);
	  puts
	    ("Copyright (C) 2009-2010 Charles E. Hallenbeck, Ph.D., <chuckh@ftml.net>\n");
	  puts
	    ("This is free software; see the file COPYING for legal details.  There is NO");
	  puts
	    ("warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\n");
	  exit (0);
	case 'w':		/* words per minute */
	  i = atoi (optarg);
	  if (i < 60 || i > 300)
	    printf ("Words-per-minute, %d, must be between 60 and 300.\n", i);
	  else
	    wordsPerMinute = i;
	  break;
	case 'z':		/* zap (overwrite) output files */
	  zaptarget = zapsource = false;
	  i = atoi (optarg);
	  if (i < 1 || i > 3)
	    break;
	  if (i & 1)
	    zapsource = true;
	  if (i & 2)
	    zaptarget = true;
	  break;
	case '?':		/* '?' */
	  break;
	}			/* end switch */
    }				/* end while */

/* double check TTS engines */
  if (!helperstatus[swift] && !helperstatus[tts])
    {
      if ((helperstatus[tts] = lookfor ("flite")))
	ttsName = xstrdup ("flite");
    }


  for (i = optind; i < argc; i++)
    add2list (argv[i]);
  for (i = 0, fnext = fhead; fnext; fnext = fnext->next)
    i++;
  if (verbosity && i > 1)
    printf ("Found %d files.\n\n", i);
  if (newest && i > 1)
    for (fnewest = fhead, fnext = fhead->next; fnext; fnext = fnext->next)
      if (fnext->age > fnewest->age)
	fnewest = fnext;

  if (converting)
    {
      if (i == 0)
	puts ("No file found.");
      else if (i > 1 && newname)
	puts ("Only one file at a time when giving the name to be used.");
      else
	error = reformat (channels, rate, newname, newtype);
    }
  else
    editmode ();

  if (verbosity)
    puts ("Done.");
  unlink ("/var/tmp/quiet.edway");
  unlink (backuptext);
  unlink (backupwave);
  return error;
}				/* main */

void
getconfig (void)
{
  short i;
  short n;
  char buf[256];
  struct stat fs;
  struct passwd *pw = NULL;
  FILE *fin;
  char *rs;
  int rv;

/* Are the suffix and helper tables built okay? */
  if (r_table != r_enums || w_table != w_enums || h_table != h_enums
      || c_table != c_enums)
    {
      fputs
	("Mismatching count of readable/writable suffix, helper, or cmd tables:",
	 stderr);
      fprintf (stderr, "Readable enums = %d, table = %d.\n", r_enums,
	       r_table);
      fprintf (stderr, "Writable enums = %d, table = %d.\n", w_enums,
	       w_table);
      fprintf (stderr, "Helper enums = %d, table = %d.\n", h_enums, h_table);
      fprintf (stderr, "Command enums = %d, table = %d.\n", c_enums, c_table);
      exit (1);
    }

/* Detect the presence of helper applications */
  for (i = 0; i < h_table; i++)
    helperstatus[i] = lookfor (helpername[i]);

/* allocate play and capture devices */
  playDevice = xstrdup ("default");
  captureDevice = xstrdup ("default");

/* Find homedir, configdir, cfg, and temp files. */
  pw = getpwuid (getuid ());
  if (!pw || !pw->pw_dir || !strlen (pw->pw_dir))
    {
      fputs ("User does not exist or lacks a home directory.\n", stderr);
      exit (1);
    }
  strcpy (buf, pw->pw_dir);
  if (buf[strlen (buf) - 1] != '/')
    strcat (buf, "/");
  strcat (buf, ".edway");
  configdir = xstrdup (buf);
  tempdir = xstrdup (buf);
  sprintf (buf, "%s/temp.txt", configdir);
  tempfile = xstrdup (buf);
  sprintf (buf, "%s/%d.txt", tempdir, getpid ());
  backuptext = xstrdup (buf);
  sprintf (buf, "%s/%d.wav", tempdir, getpid ());
  backupwave = xstrdup (buf);
  if (stat (progdir, &fs) || !S_ISDIR (fs.st_mode))
    fputs ("No doc directory available anywhere.\n", stderr);

/* Create the default configuration */
/* do we already have a configuration directory? */
  if (stat (configdir, &fs))
    {
      if (mkdir (configdir, 0755))
	{
	  fprintf (stderr, "Cannot create %s\n", configdir);
	  exit (1);
	}
      sprintf (buf, "cp %s/extras/edway.cfg %s", progdir, configdir);
      rv = system (buf);
      sprintf (buf, "cp %s/extras/*.edw %s", progdir, configdir);
      rv = system (buf);
      printf ("Created configuration file in %s\n", configdir);
    }

/* check for the sox version */
  if (helperstatus[sox])
    {
      sprintf (buf, "sox --version > %s 2>&1", tempfile);
      rv = system (buf);
      fin = fopen (tempfile, "r");
      rs = fgets (buf, 20, fin);
      fclose (fin);
      unlink (tempfile);
      buf[strlen (buf) - 1] = 0;
      soxVersion = xstrdup (buf);
      if (strcmp (soxVersion, SOXVER) < 0)
	xpfEffect = xstrdup ("filter");
      else
	xpfEffect = xstrdup ("sinc");
    }

  n = readConfig ();
  updateConfig (n);

  return;
}				/* getconfig */

int
readConfig (void)
{
  int n;
  char buf[128];
  char *ch;
  FILE *fin;
  struct stat fs;
  char *rs;

  n = 0;
  sprintf (buf, "%s/edway.cfg", configdir);
  if (!(fin = fopen (buf, "r")))
    return (n);
  rs = fgets (buf, 128, fin);
  while (!feof (fin))
    {
      if (buf[0] != '#')
	{
	  n++;
	  buf[strlen (buf) - 1] = 0;
	  while ((ch = strstr (buf, "  ")))
	    strcpy (ch, ch + 1);

	  if (!strncasecmp (buf, "AutoReduce ", 11))
	    {
	      int n;

	      n = atoi (buf + 11);
	      if (n >= 0 && n <= 3)
		autoReduce = n;
	      else
		printf ("Error in edway.cfg: %s\n", buf);
	    }
	  if (!strncasecmp (buf, "AutoRate ", 9))
	    {
	      int n;

	      n = atoi (buf + 9);
	      n = realrate (n);
	      if (n >= 10000 && n <= 50000)
		autoRate = n;
	      else
		printf ("Error in edway.cfg: %s\n", buf);
	    }
	  if (!strncasecmp (buf, "trv2other ", 10))
	    {
	      int n;

	      n = atoi (buf + 10);
	      n = realrate (n);
	      if (n >= 8000 && n <= 48000)
		trvsr = n;
	      else
		printf ("Error in edway.cfg: %s\n", buf);
	    }
	  if (!strncasecmp (buf, "DescendDir ", 11))
	    {
	      if (!strncasecmp (buf + 11, "true", 4))
		descending = true;
	      else if (!strncasecmp (buf + 11, "false", 5))
		descending = false;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "QuietFlag ", 10))
	    {
	      if (!strncasecmp (buf + 10, "true", 4))
		quietflag = true;
	      else if (!strncasecmp (buf + 10, "false", 5))
		quietflag = false;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "Newest ", 7))
	    {
	      if (!strncasecmp (buf + 7, "true", 4))
		newest = true;
	      else if (!strncasecmp (buf + 7, "false", 5))
		newest = false;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "SoundLevel ", 11))
	    {
	      int n;

	      n = atoi (buf + 11);
	      if (n < SHRT_MAX && n > 33)
		soundlevel = n;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "PlayDevice ", 11))
	    {
	      while (buf[11] == '"')
		strcpy (buf + 11, buf + 12);
	      while (buf[strlen (buf) - 1] == '"')
		buf[strlen (buf) - 1] = 0;
	      if (strlen (buf) > 12)
		{
		  free (playDevice);
		  playDevice = strdup (buf + 11);
		}
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "CaptureDevice ", 14))
	    {
	      while (buf[14] == '"')
		strcpy (buf + 14, buf + 15);
	      while (buf[strlen (buf) - 1] == '"')
		buf[strlen (buf) - 1] = 0;
	      if (strlen (buf) > 15)
		{
		  free (captureDevice);
		  captureDevice = strdup (buf + 14);
		}
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "SqueezeDB ", 10))
	    {
	      double x;

	      x = abs (atof (buf + 10));
	      if (x < 70)
		squeezeDB = x;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "SqueezeKeep ", 12))
	    {
	      int n;

	      n = atoi (buf + 12);
	      if (n > 0)
		squeezeKeep = n;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "AutoCorr ", 9))
	    {
	      double x;

	      x = atof (buf + 9);
	      if (abs (x) <= 1.0)
		autoCorr = x;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "AutoDiff ", 9))
	    {
	      double x;

	      x = abs (atof (buf + 9));
	      if (x < 70)
		autoDiff = x;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "SmoothTime ", 11))
	    {
	      double x;

	      x = atof (buf + 11);
	      if (x >= 1.0 && x <= 10.0)
		smoothTime = x;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "SmoothDrop ", 11))
	    {
	      int n;

	      n = atoi (buf + 11);
	      if (n >= 0 && n <= 10)
		smoothDrop = n;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "SmoothRangeDB ", 14))
	    {
	      double x;

	      x = atof (buf + 14);
	      if (x > 0.0)
		smoothDB = x;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "LowerHertz ", 11))
	    {
	      int n;

	      n = atoi (buf + 11);
	      if (n >= 20 && n <= 20000)
		lowerHertz = n;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "UpperHertz ", 11))
	    {
	      int n = atoi (buf + 11);
	      if (n >= 20 && n <= 20000)
		upperHertz = n;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "OggQuality ", 11))
	    {
	      double x = atof (buf + 11);
	      if (x >= -1.0 && x <= 10.0)
		oggqual = x;
	      else
		cfgError (buf);
	    }
	  if (!strncasecmp (buf, "PlaylistPath ", 13))
	    {
	    }
	  if (!strncasecmp (buf, "TempPath ", 9))
	    {
	      if (strcasecmp (buf + 9, "default"))
		{
		  free (tempdir);
		  tempdir = xstrdup (buf + 9);
/* do we already have this directory? */
		  if (stat (tempdir, &fs))
		    {
		      if (mkdir (tempdir, 0755))
			{
			  fprintf (stderr, "Cannot create %s\n", tempdir);
			  exit (1);
			}
		    }
		}
	    }
	}
      rs = fgets (buf, 128, fin);
    }
  fclose (fin);
  return (n);
}				/* readConfig */

void
cfgError (char *buf)
{
  fprintf (stderr, "error in edway.cfg: %s\n", buf);
  return;
}				/* cfgError */

void
updateConfig (int n)
{
  int v1;
  int v2;
  int v3;
  char f1[128];
  char f2[128];
  char f3[128];
  char buf[256];
  int rv;

  sprintf (f1, "%s/edway.cfg", configdir);
  sprintf (f2, "%s.new", f1);
  sprintf (f3, "%s/extras/edway.cfg", progdir);
  v1 = cfgVersion (f1);
  v2 = cfgVersion (f2);
  v3 = cfgVersion (f3);
  if (v1 != v3)
    {
      if (n > 0)
	{
	  sprintf (buf, "cp %s %s", f3, f2);
	  rv = system (buf);
	  fputs
	    ("Please replace edway.cfg with edway.cfg.new, and reconcile.\n",
	     stderr);
	}
      else
	{
	  sprintf (buf, "cp %s %s", f3, f1);
	  rv = system (buf);
	  v1 = v3;
	}
    }
  if (v1 == v3 && v2 > 0)
    unlink (f2);
  return;
}				/* updateConfig */

int
cfgVersion (char *f)
{
  int version;
  FILE *fin;
  struct stat fs;
  char buf[128];
  char *ch;
  char *rs;

  version = 0;
  if (!stat (f, &fs))
    {
      if ((fin = fopen (f, "r")))
	{
	  rs = fgets (buf, 128, fin);
	  fclose (fin);
	  if ((ch = strstr (buf, "(edway.cfg=")))
	    version = atoi (ch + 11);
	}
    }
  return (version);
}				/* cfgVersion */

int
getOthers (char *arg)
{

  if (!strncasecmp (arg, "bpf", 3))
    filtering = bpf;
  else if (!strncasecmp (arg, "hpf", 3))
    filtering = hpf;
  else if (!strncasecmp (arg, "lpf", 3))
    filtering = lpf;
  if (filtering && !strncasecmp (arg + 1, "pf", 2))
    {
      int n1 = 0;
      int n2 = 0;
      char *ch;

      if ((ch = strchr (arg, '=')))
	n1 = atoi (ch + 1);
      if ((ch = strchr (arg, ',')))
	n2 = atoi (ch + 1);
      if ((n1 && n1 < 50) || (n2 && n2 < n1))
	return (1);
      if (filtering != lpf && n1)
	lowerHertz = n1;
      if (filtering == lpf && n1)
	upperHertz = n1;
      if (filtering == bpf && n2)
	upperHertz = n2;
      if (verbosity > 1)
	printf ("lower %d, upper %d.\n", lowerHertz, upperHertz);
      return (0);
    }
  if (!strncasecmp (arg, "vs=", 3))
    {
      if (arg[2] == '=' && strlen (arg) > 3)
	speedFactor = xstrdup (arg + 3);
      else
	return (1);
      speeding = true;
      return (0);
    }
  if (!strncasecmp (arg, "ek", 2))
    {
      int n;

      if (arg[2] == '=')
	{
	  n = atoi (arg + 3);
	  if (n < 1)
	    return (1);
	  echoDelay = n;
	}
      echoing = true;
      return (0);
    }
  if (!strncasecmp (arg, "sm", 2))
    {
      double x = smoothTime;
      int n = smoothDrop;
      double z = smoothDB;
      char *ch;

      if ((ch = strchr (arg, '=')))
	{
	  if (isdigit (*(ch + 1)))
	    x = atof (ch + 1);
	  if (x < 1.0)
	    x = 1.0;
	  if ((ch = strchr (ch, ',')))
	    {
	      if (isdigit (*(ch + 1)))
		n = atoi (ch + 1);
	      if (n < 0)
		n = 0;
	      if ((ch = strchr (ch + 1, ',')))
		{
		  if (isdigit (*(ch + 1)))
		    z = atof (ch + 1);
		}
	    }
	  smoothTime = x;
	  smoothDrop = n;
	  smoothDB = z;
	}
      return (0);
    }
  if (!strncasecmp (arg, "sq", 2))
    {
      int n = squeezeKeep;
      double x = squeezeDB;
      char *ch;

      if ((ch = strchr (arg, '=')))
	{
	  if (isdigit (*(ch + 1)))
	    x = atof (ch + 1);
	  if ((ch = strchr (ch, ',')))
	    {
	      if (isdigit (*(ch + 1)))
		n = atoi (ch + 1);
	    }
	  squeezeDB = x;
	  squeezeKeep = n;
	}
      return (0);
    }
  return (1);
}				/* getOthers */
