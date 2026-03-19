/* support.c -- Edway Audio Editor 
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
extern short r_table, w_table;
extern char *rsfx[];
extern char *wsfx[];
extern char *tempfile;
extern List *fhead, *ftail;
extern Session *head, *tail;
extern int soundlevel;
extern short verbosity;
extern bool converting, descending;
extern bool smoothing, squeezingp, public;
extern double squeezeDB;
extern int squeezeKeep;
extern char *soxVersion;
extern char *xpfEffect;
extern char *captureDevice;
extern bool quietflag;

void
add2list (char *fn)
{
  short sfx;
  struct stat fs;
  FILE *dir;
  List *next;
  List *list0 = NULL;
  List *list1;
  char buf[384];
  char pfx0[384];
  char pfx[384];
  char both[384];
  char *rs;
  int rv;

  if (stat (fn, &fs))
    return;
  if ((S_ISREG (fs.st_mode) || S_ISLNK (fs.st_mode))
      && (sfx = readable (fn)) >= 0)
    {
      next = (List *) xmalloc (sizeof (List));
      next->next = NULL;
      next->prev = ftail;
      if (ftail == NULL)
	fhead = next;
      else
	ftail->next = next;
      ftail = next;
      next->name = xstrdup (fn);
      strcpy (next->type, strrchr (fn, '.'));
      next->sfx = sfx;
      next->age = fs.st_mtime;
    }
  else if (descending && S_ISDIR (fs.st_mode))
    {
      rs = getcwd (pfx0, 384);	/* save the original dir */
      if (chdir (fn))		/* go to new dir      */
	printf ("Skipping directory %s\n", fn);
      else
	{
	  rs = getcwd (pfx, 384);	/* and save it */
	  if (verbosity > 1)
	    printf ("directory %s\n", pfx);
	  sprintf (buf, "ls -1 > %s", tempfile);
	  rv = system (buf);
	  rv = chdir (pfx0);	/* restore original dir */
	  if ((dir = fopen (tempfile, "r")))
	    {
	      list0 = list1 = NULL;
	      rs = fgets (buf, 384, dir);
	      while (!feof (dir))
		{
		  buf[strlen (buf) - 1] = 0;	/* drop nl char */
		  next = (List *) xmalloc (sizeof (List));
		  next->next = NULL;
		  next->name = xstrdup (buf);
		  if (!list0)
		    list0 = list1 = next;
		  else
		    {
		      list1->next = next;
		      list1 = next;
		    }
		  rs = fgets (buf, 384, dir);
		}		/* while */
	      fclose (dir);
	    }
	  unlink (tempfile);
	  while (list0)
	    {
	      sprintf (both, "%s/%s", pfx, list0->name);
	      add2list (both);
	      next = list0;
	      list0 = list0->next;
	      free (next->name);
	      free (next);
	    }
	}
    }
}				/* add2list */

int
readable (char *name)
{
  char *cp0;
  char *cp1;
  short i;
  SNDFILE *fin;
  SF_INFO sfinfo;

  sfinfo.format = 0;
  fin = sf_open (name, SFM_READ, &sfinfo);
  if (fin)
    {
      sf_close (fin);
      if ((sfinfo.format >> 16) == 1 && (sfinfo.format & 0xFFFF) != 2)
	return (r_wav);
      return (0);
    }
  if (!(cp0 = strrchr (name, '/')))
    cp0 = name;
  else
    cp0++;
  while ((cp1 = strchr (cp0, '.')))
    cp0 = cp1 + 1;
  i = strlen (cp0);
  if (i < 2 || i > 4)
    return (-1);
  for (i = 1; i < r_table; i++)
    if (!strcasecmp (cp0, rsfx[i]))
      return (i);
  return (-1);
}				/* readable */

int
writable (char *name)
{
  char *cp0;
  char *cp1;
  short i;

  if (!(cp0 = strrchr (name, '/')))
    cp0 = name;
  else
    cp0++;
  while ((cp1 = strchr (cp0, '.')))
    cp0 = cp1 + 1;
  i = strlen (cp0);
  if (i < 2 || i > 4)
    return (-1);
  for (i = 0; i < w_table; i++)
    if (!strcasecmp (cp0, wsfx[i]))
      break;
  return (i);
}				/* writable */

bool
lookfor (char *name)
{
  bool found;
  char buf[80];

  sprintf (buf, "which %s 1>/dev/null 2>&1", name);
  found = (system (buf) ? false : true);
  return (found);
}				/* lookfor */

short
voxdecoder (short b3, short b2, short b1, short b0)
{
  static short x = 0, sub = 0;
  short d, ss, n;
  short sst[49] = { 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41,
    45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157,
    173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494,
    544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411,
    1552
  };
  short ml[8] = { -1, -1, -1, -1, 2, 4, 6, 8 };
  static long res = 0;

  ss = sst[sub];
  d = ss / 8;
  if (b0)
    d += (ss / 4);
  if (b1)
    d += (ss / 2);
  if (b2)
    d += ss;
  if (b3)
    d = -d;
  x += (d - res);
  res = ((res << 2) + x) >> 3;
  n = 0;
  if (b0)
    n = 1;
  if (b1)
    n += 2;
  if (b2)
    n += 4;
  sub += ml[n];
  if (sub < 0)
    sub = 0;
  if (sub > 48)
    sub = 48;
  return (x << 3);
}				// voxdecoder

char
voxencoder (short x1, short x2)
{
  static short x0 = 0, sub = 0;
  short d, ss, n;
  char byte, b0, b1, b2, b3;
  short sst[49] = { 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41,
    45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157,
    173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494,
    544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411,
    1552
  };
  short ml[8] = { -1, -1, -1, -1, 2, 4, 6, 8 };
  static long res = 0;

  byte = b0 = b1 = b2 = b3 = 0;
  ss = sst[sub];
  d = res + (x1 - x0) / 8;
  res = ((res << 2) + (x1 >> 3)) >> 3;
  if (d < 0)
    {
      b3 = 1;
      d = abs (d);
    }
  ss = sst[sub];
  if (d >= ss)
    {
      b2 = 1;
      d -= ss;
    }
  if (d >= (ss / 2))
    {
      b1 = 1;
      d -= (ss / 2);
    }
  if (d >= (ss / 4))
    b0 = 1;
  byte |= ((b3 << 7) + (b2 << 6) + (b1 << 5) + (b0 << 4));
  n = 0;
  if (b0)
    n = 1;
  if (b1)
    n += 2;
  if (b2)
    n += 4;
  sub += ml[n];
  if (sub < 0)
    sub = 0;
  if (sub > 48)
    sub = 48;
  b0 = b1 = b2 = b3 = 0;
  ss = sst[sub];
  d = res + (x2 - x1) / 8;
  res = ((res << 2) + (x2 >> 3)) >> 3;
  if (d < 0)
    {
      b3 = 1;
      d = abs (d);
    }
  ss = sst[sub];
  if (d >= ss)
    {
      b2 = 1;
      d -= ss;
    }
  if (d >= (ss / 2))
    {
      b1 = 1;
      d -= (ss / 2);
    }
  if (d >= (ss / 4))
    {
      b0 = 1;
      d -= (ss / 4);
    }
  byte |= ((b3 << 3) + (b2 << 2) + (b1 << 1) + b0);
  n = 0;
  if (b0)
    n = 1;
  if (b1)
    n += 2;
  if (b2)
    n += 4;
  sub += ml[n];
  if (sub < 0)
    sub = 0;
  if (sub > 48)
    sub = 48;
  x0 = x2;
  return (byte);
}				// voxencoder

Session *
newSession (int n)
{
  Session *temp;
  Session *this;

  this = (Session *) xcalloc (1, sizeof (Session));
  this->prev = tail;
  if (tail == NULL)
    head = this;
  else
    tail->next = this;
  tail = this;

  if (n)
    for (temp = head; temp; temp = temp->next)
      if (temp != this && temp->number == n)
	{
	  printf ("Session #%d already exists.\n", n);
	  n = 0;
	}

  if (n == 0)
    for (n = 1; n; n++)
      {
	for (temp = head; temp; temp = temp->next)
	  if (temp->number == n)
	    break;
	if (!temp)
	  break;
      }
  tail->number = n;
  return (tail);
}				/* newSession */

void
zaplist (void)
{
  List *next, *temp;

  for (next = fhead; next; next = temp)
    {
      temp = next->next;
      if (next->name)
	free (next->name), next->name = NULL;
      free (next), next = NULL;
    }
  fhead = ftail = NULL;
  return;
}				/* zaplist */

void
zapSession (Session * this)
{
  int i;

  if (this)
    {
      if (this->data)
	free (this->data), this->data = NULL;
      if (this->label)
	free (this->label), this->label = NULL;
      if (this->source)
	free (this->source), this->source = NULL;
      if (this->target)
	free (this->target), this->target = NULL;
      this->frames = this->channels = this->samplerate = 0;
      this->blocks = this->blocksize = 0;
      this->rsfx = this->wsfx = this->point = this->number = 0;
      this->savedrate = this->millisecs = this->zfactor = 0;
      this->bstart = this->bstop = 0;
      this->clean = false;
      for (i = 0; i < 26; i++)
	this->mark[i] = 0;
    }
  return;
}				/* zapSession */

Session *
delSession (Session * this)
{
  Session *temp;

  if (this)
    {
      temp = this;
      if (this->next)
	this->next->prev = this->prev;
      else
	tail = this->prev;
      if (this->prev)
	this->prev->next = this->next;
      else
	head = this->next;
      if (this->next)
	this = this->next;
      else if (this->prev)
	this = this->prev;
      else
	this = NULL;
      if (temp)
	free (temp), temp = NULL;
    }
  return (this);
}				/* delSession */

char *
checkname (char *oldname)
{
  Session *this;
  static char buf[196];
  static char goodname[196];
  char *ch;
  short i = 0;
  short j;
  short n = strlen (oldname);

  strcpy (goodname, oldname);
  while (i < n)
    {
      n = strlen (goodname);
      for (i = 0; i < n; i++)
	{
	  if (islower (goodname[i]) && isupper (goodname[i + 1]))
	    {
	      n++;
	      for (j = n; j > i; j--)
		goodname[j + 1] = goodname[j];
	      goodname[i + 1] = '-';
	    }			/* end of if */
	}			/* end of for */
    }				/* end of while */
  for (i = 0; i < n; i++)
    {
      if (isupper (goodname[i]))
	goodname[i] = tolower (goodname[i]);
      if (goodname[i] == '.' || isalnum (goodname[i]))
	continue;
      goodname[i] = '-';
    }
  while ((ch = strchr (goodname, '.')) && (ch != strrchr (goodname, '.')))
    *ch = '-';
  while ((ch = strstr (goodname, "--")))
    strcpy (ch, ch + 1);
  while ((ch = strstr (goodname + 1, "-.")))
    strcpy (ch, ch + 1);
  if (goodname[0] == '-')
    goodname[0] = '_';
  for (this = head; this != NULL; this = this->next)
    if (this->target && !strcasecmp (this->target, goodname))
      {
	strcpy (buf, newname (NULL, goodname));
	return (buf);
      }
  return (goodname);
}				/* checkname */

char *
newname (char *dir, char *stub)
{
  static char buf[192];
  char cwd[192];
  char *cp;
  char name[192];
  char ext[8];
  struct stat fs;
  Session *this;
  int m;
  int n;
  char *rs;
  int rv;

  if (dir)
    {
      rs = getcwd (cwd, 192);
      rv = chdir (dir);
    }
  strcpy (name, stub);
  cp = strrchr (name, '.');
  if (cp == NULL)
    {
      strcpy (name, "file");
      strcpy (ext, stub);
    }
  else
    {
      *cp = 0;
      strcpy (ext, cp + 1);
      if (isdigit (name[strlen (name) - 1]))
	strcat (name, "-");
    }
  strcat (name, "0");
  m = strlen (name) - 1;
  strcpy (buf, name);
  do
    {
      n = atoi (buf + m) + 1;
      strcpy (buf + m, itoa (n));
      strcat (buf, ".");
      strcat (buf, ext);
      for (this = head; this != NULL; this = this->next)
	if (this->target != NULL && strcasecmp (this->target, buf) == 0)
	  break;
      if (this == NULL && stat (buf, &fs))
	break;
    }
  while (true);
  if (strchr (stub, '.') == NULL)
    printf ("Name %s\n", buf);
  else if (converting && dir == NULL)
    printf ("Renaming to %s\n", buf);
  if (dir)
    rv = chdir (cwd);
  return (buf);
}				/* newname */

char *
itoa (long n)
{
  static char a[12];
  long i, j, k;

  strcpy (a, "0");
  for (i = 1000000000, k = 0; i; i /= 10)
    {
      j = n / i;
      n %= i;
      if (j > 0 || k > 0)
	{
	  a[k++] = '0' + j;
	  a[k] = 0;
	}
    }
  return (a);
}				// itoa

StereoStats *
correlate (Session * this, int b1, int b2)
{
  int i;
  int f1;
  int f2;
  int frames;
  int x;
  int y;
  double lx;
  double lxx;
  double rx;
  double rxx;
  double lrx;
  double sl;
  double sr;
  static StereoStats a;

  a.c1max = a.c1min = a.c2max = a.c2min = a.c1dc = a.c2dc = 0;
  f1 = this->blocksize * (b1 - 1);
  if (b2 < this->blocks)
    f2 = this->blocksize * b2;
  else
    f2 = this->frames;
  frames = f2 - f1;
  if (frames < this->samplerate / 1000)
    {
      puts ("too short.");
      return (&a);
    }
  lx = 0.0;
  lxx = 0.0;
  rx = 0.0;
  rxx = 0.0;
  lrx = 0.0;
  for (i = f1; i < f2; i++)
    {
      x = this->data[i * 2];
      a.c1dc += x;
      if (x > a.c1max)
	a.c1max = x;
      if (x < a.c1min)
	a.c1min = x;
      y = this->data[2 * i + 1];
      a.c2dc += y;
      if (y > a.c2max)
	a.c2max = y;
      if (y < a.c2min)
	a.c2min = y;
      lx += x;
      rx += y;
      lxx += (x * x);
      rxx += (y * y);
      lrx += (x * y);
    }
  sl = sqrt (lxx / frames);
  sr = sqrt (rxx / frames);
  a.c1db = rms2db (sl);
  a.c2db = rms2db (sr);
  a.chancorr = pearson (frames, lx, rx, lxx, rxx, lrx);
  a.c1max /= 327;
  a.c1min /= -327;
  a.c1dc /= frames;
  a.c2max /= 327;
  a.c2min /= -327;
  a.c2dc /= frames;
  return (&a);
}				/* correlate */

StereoBars *
stereobar (Session * this, int b1, int b2)
{
  int i;
  int j;
  int f1;
  int f2;
  int frames;
  int x;
  int y;
  static StereoBars a;
  double s1 = NBARS;
  double s2 = 65500;

  for (i = 0; i < NBARS; i++)
    a.ch1bar[i] = a.ch2bar[i] = 0;
  f1 = this->blocksize * (b1 - 1);
  if (b2 < this->blocks)
    f2 = this->blocksize * b2;
  else
    f2 = this->frames;
  frames = f2 - f1;
  if (frames < this->samplerate / 1000)
    {
      puts ("too short.");
      return (&a);
    }
  s1 /= 2;
  s2 /= NBARS;
  for (i = f1; i < f2; i++)
    {
      x = this->data[i * 2];
      a.ch1bar[j = s1 + x / s2]++;
      y = this->data[2 * i + 1];
      a.ch2bar[j = s1 + y / s2]++;
    }
  return (&a);
}				/* stereobar */

double
db2rms (double db)
{
  double rms;

  rms = soundlevel * exp (db * log (10.0) / 20.0);
  return (rms);
}				/* db2rms */

double
pearson (int n, double x, double y, double x2, double y2, double xy)
{
  double t1;
  double t2;
  double t3;
  double r;

  t1 = n * xy - x * y;
  t2 = n * x2 - x * x;
  t3 = n * y2 - y * y;
  if (t2 < 1.0 || t3 < 1.0)
    return (0);
  r = t1 / sqrt (t2 * t3);
  return (r);
}				/* pearson */

short
setChannels (Session * this, int mode0)
{
  int i;
  int j;
  int k;
  int samples = this->frames * this->channels;

  if (mode0 == 0)
    mode0 = this->channels;
  if (mode0 < 1 || mode0 > 4)
    {
      printf ("Mode %d: must be between 1 and 4.\n", mode0);
      return (1);
    }
  if (this->channels == mode0)
    return (0);
  if (this->channels == 2 && mode0 == 1)	/* stereo to mono */
    {
      for (i = j = 0; j < this->frames; i += 2, j++)
	{
	  k = this->data[i] + this->data[i + 1];
	  this->data[j] = k >> 1;
	}
      this->data =
	(short *) x_realloc (this->data, (this->frames + 1) * sizeof (short));
      this->channels = mode0;
      if (verbosity > 1)
	puts ("New mode mono");
    }
  if (this->channels == 2 && mode0 == 3)	/* left channel to mono */
    {
      for (i = j = 0; j < this->frames; i += 2, j++)
	this->data[j] = this->data[i];
      this->data =
	(short *) x_realloc (this->data, (this->frames + 1) * sizeof (short));
      this->channels = mode0 = 1;
      if (verbosity > 1)
	puts ("New mode mono from left");
    }
  if (this->channels == 2 && mode0 == 4)	/* right channel to mono */
    {
      for (i = j = 0; j < this->frames; i += 2, j++)
	this->data[j] = this->data[i + 1];
      this->data =
	(short *) x_realloc (this->data, (this->frames + 1) * sizeof (short));
      this->channels = mode0 = 1;
      if (verbosity > 1)
	puts ("New mode mono from right");
    }
  if (this->channels == 1 && mode0 == 2)	/* mono to stereo */
    {
      samples *= 2;
      this->data =
	(short *) x_realloc (this->data, (samples) * sizeof (short));
      for (i = samples / 2, j = samples; i; i--)
	{
	  this->data[--j] = this->data[i - 1];
	  this->data[--j] = this->data[i - 1];
	}
      this->channels = mode0;
      if (verbosity > 1)
	puts ("New mode stereo");
    }
  if (this->channels == 1 && mode0 == 3)	/* mono to left */
    {
      samples *= 2;
      this->data =
	(short *) x_realloc (this->data, (samples + 1) * sizeof (short));
      for (i = samples / 2, j = samples; i; i--)
	{
	  this->data[--j] = 0;
	  this->data[--j] = this->data[i - 1];
	}
      this->channels = mode0 = 2;
      if (verbosity > 1)
	puts ("New mode stereo left only");
    }
  if (this->channels == 1 && mode0 == 4)	/* mono to right */
    {
      samples *= 2;
      this->data =
	(short *) x_realloc (this->data, (samples + 1) * sizeof (short));
      for (i = samples / 2, j = samples; i; i--)
	{
	  this->data[--j] = this->data[i - 1];
	  this->data[--j] = 0;
	}
      this->channels = mode0 = 2;
      if (verbosity > 1)
	puts ("New mode stereo right only");
    }
  return (0);
}				/* setChannels */

short
setSamplerate (Session * this, int rate0)
{
  int i;
  int j;
  int k;
  int rate1;
  int samples = this->frames * this->channels;
  SNDFILE *sndf;
  SF_INFO sfinfo;
  double x;
  char file1wav[256];
  char file2wav[256];
  FILE *rf;

  if (rate0 == 0)
    rate0 = this->samplerate;
  if (rate0 < 5000 || rate0 > 50000)
    {
      printf ("Rate %d: must be between 5000 and 50000.\n", rate0);
      return (1);
    }
  if (this->samplerate == rate0)
    return (0);
  rate1 = this->samplerate;

  if (this->samplerate != rate0)	/* change rate with or without sox */
    {
/* we can multiply or divide by two without sox */
      if (this->samplerate * 2 == rate0)
	{
	  samples *= 2;
	  this->samplerate *= 2;
	  this->frames = samples / this->channels;
	  this->data =
	    (short *) x_realloc (this->data, (samples + 1) * sizeof (short));
	  for (j = samples / 2, i = samples; j; j--, i -= 2)
	    this->data[i - 2] = this->data[i - 1] = this->data[j - 1];
	  if (this->channels == 2)
	    for (i = 0; i < samples; i += 4)
	      {
		j = this->data[i + 1];
		this->data[i + 1] = this->data[i + 2];
		this->data[i + 2] = j;
		if (i)
		  {
		    j = this->data[i] + this->data[i - 2];
		    this->data[i - 2] = j / 2;
		    j = this->data[i + 1] + this->data[i - 1];
		    this->data[i - 1] = j / 2;
		  }
	      }
	  else
	    for (i = 2; i < samples; i += 2)
	      {
		j = this->data[i] + this->data[i - 1];
		this->data[i - 1] = j / 2;
	      }
	  this->frames = samples / this->channels;
	}
      else if (rate0 * 2 == this->samplerate)
	{
	  for (i = 3, j = 0; i < samples; i += 4)
	    {
	      k = this->data[i - 3] + this->data[i - 3 + this->channels];
	      this->data[j++] = k / 2;
	      k = this->data[i] + this->data[i - this->channels];
	      this->data[j++] = k / 2;
	    }
	  samples /= 2;
	  this->samplerate /= 2;
	  this->frames = samples / this->channels;
	  this->data =
	    (short *) x_realloc (this->data, (samples + 1) * sizeof (short));
	}
      else
/* divisors or multipliers other than two need sox */
	{
	  char rate1[8];
	  int status;
	  pid_t cpid, w;

	  sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
	  sfinfo.samplerate = this->samplerate;
	  sfinfo.channels = this->channels;;
	  sprintf (file1wav, "%s/f%dd.wav", tempdir, (int) getpid ());
	  sndf = sf_open (file1wav, SFM_WRITE, &sfinfo);
	  if (sf_error (sndf))
	    {
	      puts ("Error opening the file.");
	      return (1);
	    }
	  i = sf_writef_short (sndf, this->data, this->frames);
	  if (sf_error (sndf))
	    {
	      puts ("Error writing the file.");
	      return (1);
	    }
	  sf_close (sndf);
	  sprintf (rate1, "%d", rate0);
	  if (verbosity > 1)
	    {
	      printf ("new sampling rate, ");
	      fflush (stdout);
	    }
	  sprintf (file2wav, "%s/f%de.wav", tempdir, (int) getpid ());
	  cpid = fork ();
	  if (cpid == 0)
	    {
	      rf = freopen ("/dev/null", "w", stdout);
	      rf = freopen ("/dev/null", "w", stderr);
	      execlp ("nice", "nice", "sox", file1wav, file2wav,
		      "rate", rate1, (char *) NULL);
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
	  if (verbosity > 1)
	    puts ("done.");
	  unlink (file1wav);
	  sfinfo.format = 0;
	  sndf = sf_open (file2wav, SFM_READ, &sfinfo);
	  if (sf_error (sndf))
	    {
	      puts ("Error opening the file.");
	      return (1);
	    }
	  this->samplerate = sfinfo.samplerate;
	  this->frames = sfinfo.frames;
	  this->data =
	    (short *) x_realloc (this->data,
				 (this->frames * this->channels + 1) *
				 sizeof (short));
	  i = sf_readf_short (sndf, this->data, this->frames);
	  if (sf_error (sndf))
	    {
	      puts ("Error reading the file.");
	      return (1);
	    }
	  sf_close (sndf);
	  unlink (file2wav);
	}
      setBlocks (this, this->millisecs, 0);
      x = (1.0 * rate0) / rate1;
      for (i = 0; i < 26; i++)
	this->mark[i] *= x;
      if (verbosity > 1)
	printf ("New rate %d", this->samplerate);
    }
  return (0);
}				/* setSamplerate */

short
setType (Session * this, char *type)
{
  short i;
  char buf[80];
  char *ch;

  if (!type || strlen (type) < 1)
    return (0);
  for (i = 0; i < w_table; i++)
    if (!strcmp (type, wsfx[i]))
      break;
  if (i == w_table)
    return (1);
  if (!(ch = strrchr (this->target, '.')))
    return (1);
  else
    *ch = 0;
  sprintf (buf, "%s.%s", this->target, type);
  free (this->target);
  this->target = xstrdup (buf);
  return (0);
}				/* setType */

short
setFParms (Session * this, int channels0, int rate0)
{

  if (!this)
    return (1);
  if (channels0 == 0)
    channels0 = this->channels;
  if (rate0 == 0)
    rate0 = this->samplerate;
  if (channels0 < 1 || channels0 > 2)
    {
      printf ("Channels %d, must be 1 or 2.\n", channels0);
      return (1);
    }
  if (rate0 < 5000 || rate0 > 50000)
    {
      printf ("Sample rate %d, must be between 5000 and 50000.\n", rate0);
      return (1);
    }
  if (this->channels != channels0)
    {
      this->channels = channels0;
      printf ("False channels %s.\n",
	      (char *) (channels0 == 1 ? "mono" : "stereo"));
    }
  if (this->samplerate != rate0)
    {
      this->samplerate = rate0;
      printf ("False sample rate %d.\n", rate0);
    }
  return (0);
}				/* setFParms */

bool
setName (Session * this, char *name)
{
  char buf[128], *ch;

  if (!this || !name || strlen (name) < 1)
    return (0);
  strcpy (buf, name);
  if (!(ch = strrchr (buf, '.')) && !this->target)
    return (1);
  if (ch)			/* we have an old name, but the new one includes a suffix */
    {
      if (ch == buf || !isalnum (buf[0]))
	return (1);
      if (strlen (ch) < 2)
	strcpy (ch, strrchr (this->target, '.'));
      if (writable (buf) == w_table)
	return (1);
      free (this->target);
      this->target = xstrdup (buf);
    }
  else
    {
      strcat (buf, strrchr (this->target, '.'));
      free (this->target);
      this->target = xstrdup (buf);
    }
  return (0);
}				/* setName */

void
sanitize (Session * this, short level, bool normal)
{
  int i;
  int j;
  int k;
  int n;
  int x;
  int dc;
  int samples = this->frames * this->channels;
  int size = this->samplerate * this->channels;
  short *s;
  int sum = 0;

  if (samples < size * 2)
    size = samples / 2;
  if (this->empty || (normal && this->clean))
    return;
  this->clean = true;
  if (normal && verbosity)
    {
      printf ("Cleaning, ");
      fflush (stdout);
    }
  s = (short *) xcalloc (size + 1, sizeof (short));
/* first loop is only a test */
  for (k = 0; k < size; k++)
    sum += (this->data[k]);
  for (i = j = 0, n = size; i < samples; i++, k++)
    {
      if (i < size)
	n++;
      if (k < samples)
	x = (this->data[k]);
      else
	{
	  n--;
	  x = 0;
	}			// we have our x
      sum += x;
      s[j] = this->data[i];
      if (++j == size)
	j = 0;
      sum -= s[j];
      dc = sum / n;
      x = this->data[i] - dc;
      if (x > SHRT_MAX || x < SHRT_MIN)
	break;
    }				// end of for
  if (i < samples)
    down6db (this);
  for (k = sum = 0; k < size; k++)
    {
      s[k] = 0;
      sum += this->data[k];
    }
  for (i = j = 0, n = size; i < samples; i++, k++)
    {
      if (i < size)
	n++;
      if (k < samples)
	x = this->data[k];
      else
	{
	  n--;
	  x = 0;
	}			// we have our x
      sum += x;
      s[j] = this->data[i];
      if (++j == size)
	j = 0;
      sum -= s[j];
      dc = sum / n;
      this->data[i] -= dc;
    }				// end of for
  free (s), s = NULL;
  amplify (this, 1, this->blocks, level);
  return;
}				// sanitize

double
amplify (Session * this, int b1, int b2, int level)
{
  int i;
  int f1;
  int f2;
  int x;
  int clamp;
  int samples;
  double loudness;
  double factor;
  double sxx;

  f1 = this->blocksize * this->channels * (b1 - 1);
  if (b2 < this->blocks)
    f2 = this->blocksize * this->channels * b2;
  else
    f2 = this->frames * this->channels;
  sxx = 0;
  clamp = 0;
  samples = f2 - f1;
  if (samples < this->samplerate / 5)
    {
      puts ("Too short to amplify reliably.");
      return (0);
    }
  for (i = f1; i < f2; i++)
    {
      x = this->data[i];
      if (clamp < abs (x))
	clamp = abs (x);
      sxx += x * x;
    }
  loudness = sqrt (sxx / samples);
  if ((loudness / level) < 0.01)
    factor = 100.0;
  else
    factor = level / loudness;
  if ((clamp * factor) > PEAKMAX)
    factor = PEAKMAX / clamp;
  if (factor < 0.99 || factor > 1.01)
    {
      for (i = f1; i < f2; i++)
	this->data[i] *= factor;
    }
  return (rms2db (loudness * factor));
}				// amplify

MonoStats *
amplitude (Session * this, int b1, int b2)
{
  int i;
  int j;
  int k;
  int f1;
  int f2;
  int x;
  int samples;
  double sxx;
  double txx;
  int nseg;
  int nsam;
  int nx = 0;
  unshort rms;
  unshort tmp;
  unshort *low7 = NULL;
  unshort *high7 = NULL;
  static MonoStats a;

  f1 = this->blocksize * this->channels * (b1 - 1);
  if (b2 < this->blocks)
    f2 = this->blocksize * this->channels * b2;
  else
    f2 = this->frames * this->channels;
  samples = f2 - f1;
  a.max = a.min = a.db = a.dc = a.rms = a.rms7 = a.rms93 = 0;
  if (samples < this->samplerate / 4)
    return (&a);
  nseg = samples / (this->samplerate * this->channels * DRLEN);
  nsam = samples / nseg;
  if (nseg > DRCUT)
    {
      nx = DRTAIL * nseg;
      low7 = (unshort *) xcalloc (nx, sizeof (unshort));
      high7 = (unshort *) xcalloc (nx, sizeof (unshort));
      for (i = 0; i < nx; i++)
	low7[i] = USHRT_MAX;
    }
  sxx = txx = 0;
  for (i = f1; i < f2; i++)
    {
      x = this->data[i];
      a.dc += x;
      if (x > a.max)
	a.max = x;
      if (x < a.min)
	a.min = x;
      sxx += x * x;
      if (nseg <= DRCUT)
	continue;
      if (i && (i % nsam) == 0)
	{
	  rms = sqrt (txx / nsam);
	  tmp = rms;
	  for (k = 0; k < nx; k++)
	    if (tmp < low7[k])
	      {
		j = low7[k];
		low7[k] = tmp;
		tmp = j;
	      }
	  tmp = rms;
	  for (k = 0; k < nx; k++)
	    if (tmp > high7[k])
	      {
		j = high7[k];
		high7[k] = tmp;
		tmp = j;
	      }
	  txx = 0;
	}
      txx += x * x;
    }
  a.rms = sqrt (sxx / samples);
  a.db = rms2db (a.rms);
  a.dc /= samples;
  a.max /= 327;
  a.min /= -327;
  if (nseg > DRCUT)
    {
      a.rms7 = low7[nx - 1];
      a.rms93 = high7[nx - 1];
      free (low7);
      free (high7);
    }
  return (&a);
}				// amplitude

int *
monobar (Session * this, int b1, int b2)
{
  int i;
  int j;
  int f1;
  int f2;
  int x;
  int samples;
  static int bar[NBARS];
  double s1 = NBARS;
  double s2 = 65500;

  for (i = 0; i < NBARS; i++)
    bar[i] = 0;
  f1 = this->blocksize * this->channels * (b1 - 1);
  if (b2 < this->blocks)
    f2 = this->blocksize * this->channels * b2;
  else
    f2 = this->frames * this->channels;
  samples = f2 - f1;
  if (samples < this->samplerate / 1000)
    {
      puts ("too short.");
      return (NULL);
    }
  s1 /= 2;
  s2 /= NBARS;
  for (i = f1; i < f2; i++)
    {
      x = this->data[i];
      bar[j = s1 + x / s2]++;
    }
  return (bar);
}				// monobar

double
rms2db (double rms)
{
  double db;

  if (rms < 1.0)
    rms = 1.0;
  db = 20.0 * log10 (rms / soundlevel);
  return (db);
}				/* rms2db */

char *
playtime (Session * this, double x)
{
  static char a[132];
  double f = 0.0;
  double l = 0.0;
  int hr = 0;
  int mm = 0;
  int ss = 0;
  int ms = 0;

  l = x * this->frames / (this->samplerate * 100);
  ss += l;
  f += (l - ((int) l));
  ms = (1000 * (f - ((int) f)));
  ss += f;
  mm = (ss / 60);
  ss %= 60;
  hr = (mm / 60);
  mm %= 60;
  if (hr)
    sprintf (a, "%dh%dm%d.%03d", hr, mm, ss, ms);
  else
    sprintf (a, "%dm%d.%03d", mm, ss, ms);
  return (a);
}				/* playtime */

void
squeezit (Session * this, int b1, int b2, int db, int keep)
{
  short *s = NULL;
  int i;
  int j;
  int k;
  int s1;
  int s2;
  int samples = this->frames * this->channels;
  int region;
  int n1;
  int n2;
  int n3;
  double sxx;
  int rms;

  if (this->empty || this->frames < this->samplerate / 2)
    {
      puts ("nothing to squeeze.");
      return;
    }
  sanitize (this, soundlevel, true);
  if (verbosity)
    {
      printf ("Squeezing, ");
      fflush (stdout);
    }
  s1 = this->blocksize * this->channels * (b1 - 1);
  if (b2 < this->blocks)
    s2 = this->blocksize * this->channels * b2;
  else
    s2 = samples;
  region = s2 - s1;
  rms = db2rms (-abs (db));
  n1 = this->samplerate * this->channels / 10;	/* samples per interval */
  n2 = region / n1;		/* number of whole intervals */
  if (region % n1)
    n2++;
  s = (short *) xcalloc (n2 + 1, sizeof (short));
  sxx = 0;
  j = k = 0;
  for (i = 0; i < region; i++)
    if (i == 0 || i % n1)	/* inside an interval? */
      sxx += (this->data[s1 + i] * this->data[s1 + i]);
    else
      {
	s[j++] = (short) sqrt (sxx / n1);
	sxx = this->data[s1 + i] * this->data[s1 + i];
      }
  i = region % n1;
  if (i == 0)
    i = n1;
  s[j] = (short) sqrt (sxx / i);
/* mark removable intervals */
  for (i = 0; i < n2 + 1; i++)
    if (s[i] > rms)
      s[i] = 0;
    else
      {
	if (i == 0 || n2 == i)
	  s[i] = 1;
	else
	  s[i] = s[i - 1] + 1;
	if (s[i] > PEAKMAX)
	  s[i] = PEAKMAX;
      }
/* adjust right half of silent periods */
  for (i = 0; i < n2 + 1; i++)
    if (n2 > i && (s[i] - s[i + 1]) > 2)
      {
	s[i] = s[i + 1] + 1;
	if (i > 2)
	  i -= 3;
	else
	  i = 0;
      }
/* count removable intervals */
  for (i = n3 = 0; i < n2 + 1; i++)
    if (s[i] > keep)
      n3++;
  if (n3 == 0)
    {
      if (verbosity > 1)
	printf ("no silences");
      if (verbosity)
	printf (", duration %s.\n", playtime (this, 100));
      free (s);
      s = NULL;
      return;
    }
/* overwrite silent intervals */
  for (i = 0, j = s1; i < region; i++)
    if (s[i / n1] <= keep)
      this->data[j++] = this->data[s1 + i];
  i += s1;
  while (i < samples)
    this->data[j++] = this->data[i++];
  this->frames = j / this->channels;
  setBlocks (this, this->millisecs, 0);
  amplify (this, 1, this->blocks, soundlevel);
  k = (100.0 * (i - j)) / samples;
  free (s);
  s = NULL;
  this->data = (short *) x_realloc (this->data, (j + 1) * sizeof (short));
  if (verbosity > 1)
    {
      if (k)
	printf ("cut %d%%, or", k);
      else
	printf ("cut");
      printf (" %d silenc%s", n3, (char *) (n3 == 1 ? "e" : "es"));
    }
  if (verbosity)
    printf (", duration %s.\n", playtime (this, 100));
  return;
}				/* squeezit */

void
smoothit (Session * this, int b1, int b2, double span, int drop, double db)
{
  int i;
  int j;
  int k;
  int s1;
  int s2;
  int n;
  int nseg;
  int x;
  int region;
  int size;
  double dr0 = 0;
  double dr1 = 0;
  double rmsGlobal;
  double sxx = 0.0;
  double rms = 0.0;
  double gradient = PEAKMAX;
  double max = 0.0;
  double factor = 0.0;
  double linear;
  MonoStats *a;
  short *s;

  if (this->empty)
    {
      puts ("No data to smooth.");
      return;
    }
  sanitize (this, soundlevel, true);
  s1 = this->blocksize * this->channels * (b1 - 1);
  if (b2 < this->blocks)
    s2 = this->blocksize * this->channels * b2;
  else
    s2 = this->frames * this->channels;
  region = s2 - s1;
  size = this->samplerate * this->channels * span / 2;
  if (region < size)
    {
      puts ("Too short for smoothing.");
      return;
    }
// find rmsGlobal
  nseg = region / (this->samplerate * this->channels * DRLEN);
  a = amplitude (this, b1, b2);
  dr0 = rms2db (a->rms93) - rms2db (a->rms7);
  if (verbosity > 1 && nseg > DRCUT)
    printf ("Sound level %0.1f dB, 7%% = %.1f dB, 93%% = %.1f dB.\n",
	    a->db, rms2db (a->rms7), rms2db (a->rms93));
  if (nseg > DRCUT && dr0 < db)
    {
      printf ("Without smoothing, dynamic range is only %0.1f dB.\n", dr0);
      return;
    }
  if (verbosity)
    {
      printf ("%s smoothing ", (char *) (public ? "Public" : "Private"));
      fflush (stdout);
    }
  // find max and factor that prevent clipping
  rmsGlobal = a->rms;
  sxx = 0.0;
  for (n = 0; n < size; n++)
    sxx += this->data[s1 + n] * this->data[s1 + n];
  for (i = 0, j = region - size; i < region; i++)
    {
      if (i < size)
	n++;
      if (i < j)
	x = this->data[s1 + i + size];
      else
	{
	  n--;
	  x = 0;
	}			// we have our x
      sxx += x * x;
      if (i >= size)
	{
	  x = this->data[s1 + i - size];
	  sxx -= x * x;
	}
      rms = sqrt (sxx / n);
      if (rms < rmsGlobal)
	rms = (5.0 * rms + drop * rmsGlobal) / (drop + 5.0);
      factor = soundlevel * abs (this->data[s1 + i]) / rms;
      if (max < factor)
	max = factor;
    }				// end of for
  gradient /= max;
  linear = gradient * soundlevel;
// do the bending here
  s = (short *) xcalloc (size + 8, sizeof (short));
  sxx = 0.0;
  for (k = 0; k < size; k++)
    {
      s[k] = 0;
      sxx += this->data[s1 + k] * this->data[s1 + k];
    }				// s, sx, and sxx initialized
  for (i = j = 0, n = size; i < region; i++, k++)
    {
      if (i < size)
	n++;
      if (k < region)
	x = this->data[s1 + k];
      else
	{
	  n--;
	  x = 0;
	}			// we have our x
      sxx += x * x;
      x = s[j];
      s[j] = this->data[s1 + i];
      if (++j == size)
	j = 0;
      sxx -= x * x;
      rms = sqrt (sxx / n);
      if (rms < rmsGlobal)
	rms = (2.0 * rms + drop * rmsGlobal) / (drop + 2.0);
      if (!public)
	x = linear * this->data[s1 + i] / rms;
      else
	{
	  x = soundlevel * this->data[s1 + i] / rms;
	  factor = (max - abs (x)) / max;
	  x *= (factor + gradient - factor * gradient);
	}
      this->data[s1 + i] = x;
    }				// end of for
  free (s), s = NULL;
  amplify (this, b1, b2, soundlevel);
  a = amplitude (this, b1, b2);
  dr1 = rms2db (a->rms93) - rms2db (a->rms7);
  if (verbosity)
    {
      printf ("%.1f dB", a->db);
      if (dr0 > 0 || dr1 > 0)
	printf (", dynamic range %.1f is now %.1f dB.\n", dr0, dr1);
      else
	puts (".");
    }
  if (verbosity > 1 && nseg > DRCUT)
    printf ("Sound level %0.1f dB, 7%% = %.1f dB, 93%% = %.1f dB.\n",
	    a->db, rms2db (a->rms7), rms2db (a->rms93));
  return;
}				// smoothit

short
kbps (Session * this)
{
  short kb = 16;

  if (this->samplerate > 14000)
    kb = 32;
  if (this->samplerate > 27000)
    kb = 40;
  if (this->samplerate > 38000)
    kb = 56;
  if (this->samplerate > 46000)
    kb = 64;
  if (this->channels == 2)
    kb *= 2;
  return (kb);
}				/* end of kbps */

Command *
newCommand (Session * this)
{
  static Command a;
  char *cl1 = "$'+,-.";
  char buf[256];
  char *ch;
  int i;
  double x;

/* adjust the prompt and get a command */
  if (!head)
    strcpy (buf, "\nEdway ready: * ");
  else if (head == tail)
    strcpy (buf, "\n* ");
  else
    sprintf (buf, "\n#%d: * ", this->number);
  if (a.cmd)
    free (a.cmd), a.cmd = NULL;
  a.arg = NULL;
  a.address1 = a.address2 = a.address3 = a.number = 0;
  while (!(a.cmd = readline (buf)));

  x = 0;
  ch = a.cmd;
  if (this && (strchr (cl1, *ch) || isdigit (*ch)))
    {
      if (strlen (ch) < 1)	/* get address1 */
	{
	  if (this->point < this->blocks)
	    this->point++;
	  a.address1 = this->point;
	}
      else if (*ch == ',')
	a.address1 = 1;
      else if (isdigit (*ch))
	{
	  a.address1 = atoi (ch);
	  while (isdigit (*ch))
	    ch++;
	}
      else if (*ch == '.')
	{
	  a.address1 = this->point;
	  ch++;
	}
      else if (*ch == '-')
	for (a.address1 = this->point; *ch == '-'; ch++)
	  {
	    if (isdigit (ch[1]))
	      {
		i = atoi (ch + 1);
		while (isdigit (ch[1]))
		  ch++;
		a.address1 -= i;
	      }
	    else
	      a.address1--;
	  }
      else if (*ch == '+')
	for (a.address1 = this->point; *ch == '+'; ch++)
	  {
	    if (isdigit (ch[1]))
	      {
		i = atoi (ch + 1);
		while (isdigit (ch[1]))
		  ch++;
		a.address1 += i;
	      }
	    else
	      a.address1++;
	  }
      else if (*ch == '$')
	{
	  a.address1 = this->blocks;
	  ch++;
	}
      else if (*ch == TICK && islower (*(ch + 1)))
	{
	  i = *(ch + 1);
	  i -= 'a';
	  if (this->mark[i])
	    a.address1 = 1 + (this->mark[i] - 1) / this->blocksize;
	  else
	    printf ("label %c not set.\n", i + 'a');
	  ch++, ch++;
	}			/* end of first address */
      if (*ch == ',')		/* second address */
	{
	  ch++;
	  strcpy (a.cmd, ch);
	  ch = a.cmd;
	  a.address2 = this->blocks;
	  if (*ch == '.')
	    {
	      a.address2 = this->point;
	      ch++;
	    }
	  else if (*ch == '$')
	    ch++;
	  else if (*ch == '-')
	    for (a.address1 = this->point; *ch == '-'; ch++)
	      {
		if (isdigit (ch[1]))
		  {
		    i = atoi (ch + 1);
		    while (isdigit (ch[1]))
		      ch++;
		    a.address2 -= i;
		  }
		else
		  a.address2--;
	      }
	  else if (*ch == '+')
	    for (a.address1 = this->point; *ch == '+'; ch++)
	      {
		if (isdigit (ch[1]))
		  {
		    i = atoi (ch + 1);
		    while (isdigit (ch[1]))
		      ch++;
		    a.address2 += i;
		  }
		else
		  a.address2++;
	      }
	  else if (isdigit (*ch))
	    {
	      a.address2 = atoi (ch);
	      while (isdigit (*ch))
		ch++;
	    }
	  else if (*ch == TICK && islower (*(ch + 1)))
	    {
	      i = *(ch + 1);
	      i -= 'a';
	      if (this->mark[i])
		a.address2 = 1 + (this->mark[i] - 1) / this->blocksize;
	      else
		printf ("label %c not set.\n", i + 'a');
	      ch++, ch++;
	    }
	}
      if (a.cmd != ch)
	strcpy (a.cmd, ch);
      ch = a.cmd;
    }				/* got address1 and address2 */

  if (*ch == ',')
    return (NULL);

/* insert a space after an initial pound sign or exclamation */
  if ((*ch == '!' || *ch == '#') && isalpha (*(ch + 1)))
    {
      sprintf (buf, "%c %s", *ch, ch + 1);
      if (a.cmd)
	free (a.cmd), a.cmd = NULL;
      a.cmd = xstrdup (buf);
    }

/* find the argument string */
  a.arg = strchr (a.cmd, SPACE);
  if (!a.arg)
    a.arg = a.cmd + strlen (a.cmd);
  while (isspace (*a.arg))
    {
      *a.arg = 0;
      a.arg++;
    }
  buf[0] = 0;
  ch = a.cmd;
  if (strchr ("cejrwz", *ch) && isdigit (ch[1]))
    {
      a.number = atoi (ch + 1);
      *++ch = 0;
    }
  if (!strncasecmp (ch, "mx", 2) && isdigit (ch[2]))
    {
      a.number = atoi (ch + 2);
      ch++;
      *++ch = 0;
    }
  if (strlen (a.cmd) > 1 && (*a.cmd == 'm' || *a.cmd == 't'))
    {
      ch = a.cmd + 1;
      if (strchr (cl1, *ch) || isdigit (*ch))
	{
	  a.address3 = this->point;
	  if (*ch == '.')
	    ch++;
	  else if (*ch == '$')
	    {
	      a.address3 = this->blocks;
	      ch++;
	    }
	  else if (*ch == '-')
	    for (a.address3 = this->point; *ch == '-'; ch++)
	      a.address3--;
	  else if (*ch == '+')
	    for (a.address3 = this->point; *ch == '+'; ch++)
	      a.address3++;
	  else if (isdigit (*ch))
	    {
	      a.address3 = atoi (ch);
	      while (isdigit (*ch))
		ch++;
	    }
	  else if (*ch == TICK && islower (*(ch + 1)))
	    {
	      i = *(ch + 1);
	      i -= 'a';
	      if (this->mark[i])
		a.address3 = 1 + (this->mark[i] - 1) / this->blocksize;
	      else
		printf ("label %c not set.\n", i + 'a');
	      ch++, ch++;
	    }
	  *(a.cmd + 1) = 0;
	}
    }
/* end of cmd parsing */

  return (&a);
}				/* newCommand */

int
setBlocks (Session * this, int ms, int nb)
{
  int bs = 0;
  int resid = 0;
  long nms = (this->point - 1) * this->blocksize + 1 + this->blocksize / 2;

  if (ms && nb)
    {
      puts ("Specify either ms or nb, but not both.");
      return (-1);
    }
  if (!ms && !nb)
    {
      ms = this->millisecs;
      nb = this->blocks;
      bs = this->blocksize;
      resid = this->frames - (nb * bs);
      printf ("%d blocks of %d ms, plus %0.01f%% extra block.\n", nb, ms,
	      (100.0 * resid) / bs);
      return (0);
    }
  if (ms && ms < 1)
    {
      printf ("Bad ms value, %d: must be at least 1.\n", ms);
      return (-1);
    }
  if (nb && nb < 2)
    {
      printf ("Bad blocks value, %d: must be at least 2.\n", nb);
      return (-1);
    }

  if (ms)
    {
      int max = this->frames * (500.0 / this->samplerate);

      if (ms > max)
	ms = max;
      if (ms < 40000)
	bs = this->samplerate * ms / 1000;
      else
	bs = this->samplerate / 1000 * ms;
      nb = this->frames / bs;
      resid = this->frames - bs * nb;
    }
  else if (nb)
    {
      if (nb > this->frames / (this->samplerate / 1000))
	{
	  printf ("Value %d is too big, maximum is %d.\n", nb,
		  this->frames / (this->samplerate / 1000));
	  return (-1);
	}
      bs = this->frames / nb;
      ms = 1000 * bs / this->samplerate;
      if ((this->frames - nb * bs) > bs)
	{
	  nb = this->frames / bs;
	  printf ("Increased to %d blocks.\n", nb);
	}
      resid = this->frames - nb * bs;
    }
  if (verbosity > 1)
    printf ("%d blocks of %d ms, plus %0.01f%% extra block.\n", nb, ms,
	    (100.0 * resid) / bs);
  this->millisecs = ms;
  this->blocksize = bs;
  this->point = 1 + (nms - 1) / this->blocksize;
  this->blocks = nb;
  if (this->point > nb)
    this->point = nb;
  return (resid);
}				/* setBlocks */

int
getAddType (char *arg)
{
  int addType = 0;
  char *ch;

  if (!strncasecmp (arg, "http://", 7)
      || !strncasecmp (arg, "mms://", 6)
      || !strncasecmp (arg, "pnm://", 6) || !strncasecmp (arg, "rtsp://", 7))
    addType += 1;
  ch = strrchr (arg, '.');
  if (ch && (!strcasecmp (ch, ".asf") || !strcasecmp (ch, ".asx")
	     || !strcasecmp (ch, ".m3u") || !strcasecmp (ch, ".pls")
	     || !strcasecmp (ch, ".ram")))
    addType += 2;
  return (addType);
}				/* getAddType */

void
putSession (Session * that, int number)
{
  Session *this = NULL;
  short *data = NULL;
  int i;
  int ns;

  for (this = head; this; this = this->next)
    if (this->number == number)
      break;

  if (this)
    zapSession (this);
  else
    this = newSession (number);

  this->channels = that->channels;
  this->samplerate = that->samplerate;
  this->savedrate = that->savedrate;
  this->frames = (that->bstop - that->bstart) * that->frames + 0.5;
  ns = this->frames * this->channels;
  this->data = (short *) xcalloc (ns, sizeof (short));
  data =
    (short *) (that->data +
	       (int) (that->bstart * that->frames * that->channels + 0.5));

  for (i = 0; i < ns; i++)
    this->data[i] = data[i];

  setBlocks (this, 1000, 0);
  this->point = this->blocks;
  this->bstart = 0;
  this->bstop = 1.0;

  this->source = xstrdup (that->source);
  this->rsfx = that->rsfx;
  this->target = xstrdup ("edway.wav");
  this->wsfx = w_wav;
  this->zfactor = ZX;

  return;
}				/* putSession */

void
getSession (Session * that, int number, int where)
{
  Session temp;
  Session *this;
  int f1;
  int f2;
  int i;
  int n1;
  int n2;

  for (this = head; this; this = this->next)
    if (this->number == number)
      break;
  if (!this)
    {
      fprintf (stderr, "session #%d not found.\n", number);
      return;
    }
  f1 = (where == 1 ? 0 : where * that->blocksize * that->channels);
  f2 = that->frames * that->channels;
  if (where == that->blocks)
    f1 = f2;

  temp.samplerate = this->samplerate;
  temp.channels = this->channels;
  temp.frames = this->frames;
  temp.millisecs = this->millisecs;
  temp.blocksize = this->blocksize;
  temp.blocks = this->blocks;
  n1 = temp.frames * temp.channels;
  temp.data = (short *) xmalloc ((n1 + 1) * sizeof (short));
  for (i = 0; i < n1; i++)
    temp.data[i] = this->data[i];
  setBlocks (&temp, temp.millisecs, 0);
  if (this->channels != that->channels
      || this->samplerate != that->samplerate)
    {
      setSamplerate (&temp, that->samplerate);
      setChannels (&temp, that->channels);
    }
  n1 = temp.frames * temp.channels;
  n2 = f2 + n1;
  that->data = (short *) x_realloc (that->data, (n2 + 1) * sizeof (short));
  for (i = f2; i > f1; i--)
    that->data[i + n1 - 1] = that->data[i - 1];
  for (i = 0; i < n1; i++)
    that->data[f1 + i] = temp.data[i];
  that->frames = n2 / that->channels;
  i = that->point;
  setBlocks (that, that->millisecs, 0);
  if (i > where)
    i += temp.blocks;
  if (i > that->blocks)
    that->point = that->blocks;
  else
    that->point = i;
  for (i = 0; i < 26; i++)
    if (that->mark[i] > f1)
      that->mark[i] += n1;
  free (temp.data);
  return;
}				/* getSession */

void
joinSession (Session * that, int number)
{
  Session *this;
  int f1;
  int i;
  int n1;
  int n2;

  for (this = head; this; this = this->next)
    if (this->number == number)
      break;
  if (!this)
    {
      printf ("session #%d not found.\n", number);
      return;
    }
  f1 = that->frames * that->channels;

  if (this->channels != that->channels
      || this->samplerate != that->samplerate)
    {
      setSamplerate (this, that->samplerate);
      setChannels (this, that->channels);
    }
  n1 = this->frames * this->channels;
  n2 = f1 + n1;
  that->data = (short *) x_realloc (that->data, (n2 + 1) * sizeof (short));
  for (i = 0; i < n1; i++)
    that->data[f1 + i] = this->data[i];
  that->frames = n2 / that->channels;
  printf ("ms %d.\n", that->millisecs);
  setBlocks (that, that->millisecs, 0);
  zapSession (this);
  delSession (this);
  return;
}				/* joinSession */

void
moveBlocks (Session * this, int b1, int b2, int b3)
{
  int s1;
  int s2;
  int s3;
  int n1;
  int n2;
  int i;
  short *data;

  s1 = (b1 == 1 ? 0 : this->blocksize * this->channels * (b1 - 1));
  if (b1 == this->blocks)
    s1 = this->frames * this->channels;
  if (b2 == this->blocks)
    s2 = this->frames * this->channels;
  else
    s2 = this->blocksize * this->channels * b2;
  s3 = (b3 == 1 ? 0 : this->blocksize * this->channels * b3);
  n1 = s2 - s1 + 1;
  if (b3 < this->point && this->point <= b2)
    {
      if (this->point < b1)
	this->point += (1 + b2 - b1);
      else
	this->point -= (b1 - b3);
    }
  else if (b1 < this->point && this->point <= b3)
    {
      if (b2 <= this->point)
	this->point -= (1 + b2 - b1);
      else
	this->point += (1 + b3 - b1);
    }
  for (i = 0; i < 26; i++)
    if (b3 * this->blocksize < this->mark[i]
	&& this->mark[i] <= b2 * this->blocksize)
      {
	if (this->mark[i] < b1 * this->blocksize)
	  this->mark[i] += ((1 + b2 - b1) * this->blocksize);
	else
	  this->mark[i] -= ((b1 - b3) * this->blocksize);
      }
    else if (b1 * this->blocksize < this->mark[i]
	     && this->mark[i] <= b3 * this->blocksize)
      {
	if (b2 * this->blocksize <= this->mark[i])
	  this->mark[i] -= ((1 + b2 - b1) * this->blocksize);
	else
	  this->mark[i] += ((1 + b3 - b1) * this->blocksize);
      }
  data = (short *) xmalloc ((n1 + 1) * sizeof (short));
  for (i = 0; i < n1; i++)
    data[i] = this->data[s1 + i];
  if (s2 < s3)
    {
      n2 = s3 - s2 + 1;
      for (i = 0; i < n2; i++)
	this->data[s1 + i] = this->data[s2 + i];
      s3 -= n1;
    }
  else
    {
      n2 = s1 - s3 + 1;
      for (i = 0; i < n2; i++)
	this->data[s2 - i - 1] = this->data[s1 - i - 1];
    }
  for (i = 0; i < n1; i++)
    this->data[s3 + i] = data[i];
  free (data);
  return;
}				/* moveBlocks */

void
copyBlocks (Session * this, int b1, int b2, int b3)
{
  int s1;
  int s2;
  int s3;
  int n1;
  int n2;
  int n3;
  int i;
  short *data;

  s1 = (b1 == 1 ? 0 : this->blocksize * this->channels * (b1 - 1));
  if (b1 == this->blocks)
    s1 = this->frames * this->channels;
  if (b2 == this->blocks)
    s2 = this->frames * this->channels;
  else
    s2 = this->blocksize * this->channels * b2;
  s3 = (b3 == 1 ? 0 : this->blocksize * this->channels * b3);
  n1 = s2 - s1 + 1;
  data = (short *) xmalloc ((n1 + 1) * sizeof (short));
  for (i = 0; i < n1; i++)
    data[i] = this->data[s1 + i];
  n2 = n1 + this->frames * this->channels;
  n3 = this->frames * this->channels - s3;
  this->data = (short *) x_realloc (this->data, n2 * sizeof (short));
  this->frames = n2 / this->channels;
  i = this->point;
  setBlocks (this, this->millisecs, 0);
  if (b3 < i)
    i += (1 + b2 - b1);
  if (i > this->blocks)
    this->point = this->blocks;
  else
    this->point = i;
  for (i = 0; i < 26; i++)
    if (b3 * this->blocksize < this->mark[i])
      this->mark[i] += ((1 + b2 - b1) * this->blocksize);
  for (i = 0; i < n3; i++)
    this->data[n2 - i - 1] = this->data[n2 - n1 - i - 1];
  for (i = 0; i < n1; i++)
    this->data[s3 + i] = data[i];
  free (data);
  return;
}				/* copyBlocks */

int
memsize (Session * this)
{
  int n;

  if (this && this->data)
    n = sizeof (short) * this->channels * this->frames;
  else
    n = 0;
  return (n);
}				/* memsize */

char *
memchars (int mem)
{
  static char buf[16];

  if (mem > MB)
    sprintf (buf, "%.1fM", ((double) mem) / MB);
  else if (mem > KB)
    sprintf (buf, "%.1fK", ((double) mem) / KB);
  else
    sprintf (buf, "%dB", (int) mem);
  return (buf);
}				/* memchars */

int
soxFilter (Session * this, int lower, int upper)
{
  int i;
  char param[16];
  int status;
  pid_t cpid, w;
  SNDFILE *sndf;
  SF_INFO sfinfo;
  char file1wav[256];
  char file2wav[256];
  FILE *rf;

  sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
  sfinfo.samplerate = this->samplerate;
  sfinfo.channels = this->channels;
  sprintf (file1wav, "%s/f%df.wav", tempdir, (int) getpid ());
  sndf = sf_open (file1wav, SFM_WRITE, &sfinfo);
  if (sf_error (sndf))
    {
      puts ("Error opening the write file.");
      return (true);
    }
  i = sf_writef_short (sndf, this->data, this->frames);
  if (sf_error (sndf))
    {
      puts ("Error writing the file.");
      return (1);
    }
  sf_close (sndf);
  sprintf (param, "%d-%d", lower, upper);
  if (verbosity > 1)
    {
      printf ("Filtering, ");
      fflush (stdout);
    }
  sprintf (file2wav, "%s/f%dg.wav", tempdir, (int) getpid ());
  cpid = fork ();
  if (cpid == 0)
    {
      rf = freopen ("/dev/null", "w", stdout);
      rf = freopen ("/dev/null", "w", stderr);
      execlp ("nice", "nice", "sox", "-v0.7", file1wav, file2wav, xpfEffect,
	      param, (char *) NULL);
    }
  else
    {
      status = 0;
      while (true)
	{
	  w = waitpid (cpid, &status, WNOHANG);
	  if (w == cpid && WIFEXITED (status))
	    break;
	}			/* end while */
    }				/* end else */
  if (verbosity > 1)
    puts ("done.");
  unlink (file1wav);
  sfinfo.format = 0;
  sndf = sf_open (file2wav, SFM_READ, &sfinfo);
  if (sf_error (sndf))
    {
      puts ("Error opening the read file.");
      return (true);
    }
  this->samplerate = sfinfo.samplerate;
  this->channels = sfinfo.channels;
  this->frames = sfinfo.frames;
  this->data =
    (short *) x_realloc (this->data,
			 (this->frames * this->channels + 1) *
			 sizeof (short));
  i = sf_readf_short (sndf, this->data, this->frames);
  if (sf_error (sndf))
    {
      puts ("Error reading the file.");
      return (1);
    }
  sf_close (sndf);
  unlink (file2wav);
  setBlocks (this, this->millisecs, 0);
  amplify (this, 1, this->blocks, soundlevel);
  return (0);
}				/* soxFilter */

int
soxFactor (Session * this, double factor)
{
  int i;
  char param[16];
  int status;
  pid_t cpid;
  pid_t w;
  SNDFILE *sndf;
  SF_INFO sfinfo;
  char file1wav[256];
  char file2wav[256];
  FILE *rf;

  if (factor <= 1.0 && 1.0 <= factor)
    return (0);
  sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
  sfinfo.samplerate = this->samplerate;
  sfinfo.channels = this->channels;
  sprintf (file1wav, "%s/f%dh.wav", tempdir, (int) getpid ());
  sndf = sf_open (file1wav, SFM_WRITE, &sfinfo);
  if (sf_error (sndf))
    {
      puts ("Error opening the write file.");
      return (true);
    }
  i = sf_writef_short (sndf, this->data, this->frames);
  if (sf_error (sndf))
    {
      puts ("Error writing the file.");
      return (1);
    }
  sf_close (sndf);
  sprintf (param, "%0.03f", factor);
  if (verbosity > 1)
    {
      printf ("New tempo, ");
      fflush (stdout);
    }
  sprintf (file2wav, "%s/f%di.wav", tempdir, (int) getpid ());
  cpid = fork ();
  if (cpid == 0)
    {
      rf = freopen ("/dev/null", "w", stdout);
      rf = freopen ("/dev/null", "w", stderr);
      execlp ("nice", "nice", "sox", "-v0.7", file1wav, file2wav, "tempo",
	      param, "50", (char *) NULL);
    }
  else
    {
      status = 0;
      while (true)
	{
	  w = waitpid (cpid, &status, WNOHANG);
	  if (w == cpid && WIFEXITED (status))
	    break;
	}			/* end while */
    }				/* end else */
  if (verbosity > 1)
    puts ("done.");
  unlink (file1wav);
  sfinfo.format = 0;
  sndf = sf_open (file2wav, SFM_READ, &sfinfo);
  if (sf_error (sndf))
    {
      puts ("Error opening the read file.");
      return (1);
    }
  this->samplerate = sfinfo.samplerate;
  this->channels = sfinfo.channels;
  this->frames = sfinfo.frames;
  this->data =
    (short *) x_realloc (this->data,
			 (this->frames * this->channels + 1) *
			 sizeof (short));
  i = sf_readf_short (sndf, this->data, this->frames);
  if (sf_error (sndf))
    {
      puts ("Error reading the file.");
      return (1);
    }
  sf_close (sndf);
  unlink (file2wav);
  setBlocks (this, this->millisecs, 0);
  amplify (this, 1, this->blocks, soundlevel);
  return (0);
}				/* soxFactor */

int
captureAudio (char *arg)
{
  pid_t cpid, w;
  int status;
  int seconds;
  int key;
  char chans[] = "-c2";
  time_t time0;
  char file0wav[256];
  FILE *rf;
  int rv;

  if (!strcasecmp (arg, "line") && lookfor ("capline.edw"))
    rv = system ("capline.edw");
  else if (!strcasecmp (arg, "mike") && lookfor ("capmike.edw"))
    rv = system ("capmike.edw");
  else if (!strcasecmp (arg, "wave") && lookfor ("capwave.edw"))
    rv = system ("capwave.edw");
  if (!strcasecmp (arg, "mike"))
    strcpy (chans, "-c1");
  sprintf (file0wav, "%s/%s", tempdir, newname (tempdir, "capture.wav"));
  if (quietflag)
    rv = system ("echo \".\" > /var/tmp/quiet.edway");
  cpid = fork ();
  if (cpid == 0)
    {
      rf = freopen ("/dev/null", "w", stdout);
      rf = freopen ("/dev/null", "w", stderr);
      execlp ("arecord", "arecord", "-D", captureDevice,
	      "-fS16_LE", "-r22050", chans, file0wav, (char *) NULL);
    }
  else
    {
      status = 0;
      time0 = time (NULL);
      while (true)
	{
	  w = waitpid (cpid, &status, WNOHANG);
	  if (w == cpid && WIFEXITED (status))
	    break;
	  usleep (10000);
	  if ((key = getch ()) == ',')
	    {
	      seconds = time (NULL) - time0;
	      printf (": %dm%d.\n", seconds / 60, seconds % 60);
	    }
	  else if (key >= SPACE)
	    kill (cpid, SIGTERM);
	}
    }
  if (strlen (arg) == 4 && lookfor ("capstop.edw"))
    rv = system ("capstop.edw");
  if (quietflag)
    unlink ("/var/tmp/quiet.edway");
  if (getAudio (file0wav, 0, 0))
    return (1);
  unlink (file0wav);
  if (strlen (arg) == 4)
    {
      sanitize (tail, soundlevel, false);
      fadeIn (tail, 0.25);
      fadeOut (tail, 0.25);
    }
  return (false);
}				/* captureAudio */

bool
genAudio (Session * that, int where, int len, int form, int duty,
	  int firstF, int secondF)
{
  Session *this;
  int f1;
  int f2;
  int n1;
  int n2;
  int i;
  int n = 0;
  double two_pi = 2 * M_PI;
  double sec = len / 1000.0;
  double bias = duty / 10.0;
  double rotor;
  double logF1;
  double step;
  bool rising;
  double delta;

  if (verbosity > 1)
    printf ("%d, %d, %d, %d, %d, %d.\n", where, len, form,
	    duty, firstF, secondF);
  if (that && !that->data)
    this = that;
  else
    this = newSession (0);
  if (!that)
    that = this;
  if (this != that)
    this->savedrate = this->samplerate = that->samplerate;
  else
    this->savedrate = this->samplerate = 22050;
  this->channels = 1;
  this->frames = this->samplerate * (len / 1000.0) + 0.5;
  this->data = (short *) xcalloc (this->frames + 1, sizeof (short));
  this->blocksize = this->samplerate;
  this->blocks = this->frames / this->blocksize;
  setBlocks (this, 1000, 0);
  this->rsfx = r_wav;
  this->wsfx = w_wav;
  this->source = xstrdup ("gen.wav");
  this->target = xstrdup ("gen.wav");
  this->zfactor = ZX;
  if (form)
    switch (form)
      {
      case sine:
	if (verbosity > 1)
	  puts ("sine wave");
	logF1 = log (firstF);
	step = (log (secondF) - logF1) / this->frames;
	delta = (two_pi * sec) / this->frames;
	for (n = 0, rotor = 0.0; n < this->frames; n++)
	  {
	    this->data[n] = soundlevel * sin (rotor);
	    logF1 += step;
	    rotor += exp (logF1) * delta;
	    if (rotor > M_PI)
	      rotor -= two_pi;
	  }
	amplify (this, 1, this->blocks, soundlevel);
	break;
      case square:
	if (verbosity > 1)
	  puts ("square wave.");
	logF1 = log (firstF);
	step = (log (secondF) - logF1) / this->frames;
	delta = sec / this->frames;
	for (n = 0, rotor = 0.0; n < this->frames; n++)
	  {
	    this->data[n] = soundlevel * (rotor > bias ? -1.0 : 1.0);
	    logF1 += step;
	    rotor += exp (logF1) * delta;
	    if (rotor > 1.0)
	      rotor -= 1.0;
	  }
	sanitize (this, soundlevel, false);
	break;
      case sawtooth:
	if (verbosity > 1)
	  puts ("sawtooth.");
	rising = (bias < 0.5 ? false : true);
	logF1 = log (firstF);
	step = (log (secondF) - logF1) / this->frames;
	delta = sec / this->frames;
	if (duty == 5)
	  delta *= 2.0;
	for (n = 0, rotor = 0.0; n < this->frames; n++)
	  {
	    this->data[n] = 3.4 * soundlevel * (rising ? rotor : 1.0 - rotor);
	    logF1 += step;
	    rotor += exp (logF1) * delta;
	    if (rotor > 1.0)
	      {
		if (duty == 5)
		  rising = (rising ? false : true);
		rotor -= 1.0;
	      }
	  }
	sanitize (this, soundlevel, false);
	break;
      }				/* switch */
  if (this != that)
    {
      f1 = (where <= 1 ? 0 : where * that->blocksize * that->channels);
      f2 = that->frames * that->channels;
      if (where == that->blocks)
	f1 = f2;

      setChannels (this, that->channels);
      n1 = this->frames * this->channels;
      n2 = f2 + n1;
      that->data =
	(short *) x_realloc (that->data, (n2 + 1) * sizeof (short));
      for (n = f2; n > f1; n--)
	that->data[n + n1 - 1] = that->data[n - 1];
      for (n = 0; n < n1; n++)
	that->data[f1 + n] = this->data[n];
      that->frames = n2 / that->channels;
      if (verbosity > 1)
	printf ("ms %d.\n", that->millisecs);
      i = that->point;
      setBlocks (that, that->millisecs, 0);
      if (i > where)
	i += this->blocks;
      if (i > that->blocks)
	that->point = that->blocks;
      else
	that->point = i;
      for (i = 0; i < 26; i++)
	if (that->mark[i] > f1)
	  that->mark[i] += n1;
      zapSession (this);
      delSession (this);
    }
  return (n);
}				/* genAudio */

double
getFactor (Session * this, char *arg)
{
  double x = 1.0;

  if (!isdigit (arg[0]))
    return (1.0);
  if (!strchr (arg, 'h') && !strchr (arg, 'H') && !strchr (arg, 'm')
      && !strchr (arg, 'M'))
    x = atof (arg);
  else
    {
      char *ch;
      double seconds = 0.0;
      int hours = 0;
      int mins = 0;
      double oldtime;
      double newtime;

      oldtime = (1.0 * this->frames) / this->samplerate;
      ch = strchr (arg, 'm');
      if (!ch)
	ch = strchr (arg, 'M');
      if (ch && arg[strlen (arg) - 1] != *ch)
	seconds = atof (ch + 1);
      ch = strchr (arg, 'h');
      if (!ch)
	ch = strchr (arg, 'H');
      if (ch)
	{
	  hours = atoi (arg);
	  if (arg[strlen (arg) - 1] != *ch)
	    mins = atoi (ch + 1);
	}
      else
	mins = atoi (arg);
      newtime = hours * 3600 + mins * 60 + seconds;
      if (verbosity > 1)
	printf ("newtime %0.3f\n", newtime);
      if (newtime < oldtime * 0.8 || newtime > oldtime * 2.0)
	x = 1.0;
      else
	x = oldtime / newtime;
    }
  if (0.8 <= x && x <= 2.0)
    return (x);
  fprintf (stderr, "Factor %s: must be between 0.8 and 2.0\n", arg);
  return (1.0);
}				/* getFactor */

bool
combineAudio (Session * that, int b1, int b2, int num, double fade1,
	      double fade2)
{
  Session *temp;
  Session *this;
  double time1;
  double time2;
  double time3;
  int f1;
  int f2;
  int start;
  int samples;
  int i;

  for (this = head; this; this = this->next)
    if (this->number == num)
      break;
  if (!this)
    {
      fprintf (stderr, "session #%d not found.\n", num);
      return (true);
    }
  time1 = this->frames / (1.0 * this->samplerate);
  f1 = (b1 < 2 ? 0 : that->blocksize * (b1 - 1));
  start = f1 * that->channels;
  if (b2 < 1 || b2 >= that->blocks)
    f2 = that->frames;
  else
    f2 = (b2 >= b1 ? that->blocksize * b2 : that->frames);
  time2 = (f2 - f1) / (1.0 * that->samplerate);
  time3 = (time1 < time2 ? time1 : time2);
  temp = newSession (0);
  temp->samplerate = this->samplerate;
  temp->blocksize = this->samplerate;
  temp->channels = this->channels;
  temp->frames = time3 * this->samplerate;
  setBlocks (temp, this->millisecs, 0);
  samples = temp->frames * temp->channels;
  temp->data = (short *) xcalloc (samples, sizeof (short));
  for (i = 0; i < samples; i++)
    temp->data[i] = this->data[i];
  setChannels (temp, that->channels);
  setSamplerate (temp, that->samplerate);
  samples = temp->frames * temp->channels;
  fadeIn (temp, fade1);
  fadeOut (temp, fade2);
  down6db (temp);
  down6db (that);
  for (i = 0; i < samples; i++)
    that->data[start + i] += temp->data[i];
  zapSession (temp);
  delSession (temp);
  amplify (that, 1, that->blocks, soundlevel);
  return (false);
}				/* combineAudio */

bool
fadeIn (Session * this, double area)
{
  double x;
  int i;
  int j = this->channels;
  int n = area * this->samplerate * j;
  double dn = n;

  for (i = 0; i < n; i += j)
    {
      x = (i + 1) / dn;
      if (area <= 2.0)
	x = (0.5 - 0.5 * cos (x * M_PI));
      this->data[i] *= (x * x);
      if (j == 2)
	this->data[i + 1] *= (x * x);
    }
  return (true);
}				/* fadeIn */

bool
fadeOut (Session * this, double area)
{
  double x;
  int i;
  int j = this->channels;
  int n = area * this->samplerate * j;
  double dn = n;
  int l = this->frames - n;

  for (i = 0; i < n; i += j)
    {
      x = (n - i) / dn;
      if (area <= 2.0)
	x = (0.5 - 0.5 * cos (x * M_PI));
      this->data[l + i] *= (x * x);
      if (j == 2)
	this->data[l + i + 1] *= (x * x);
    }
  return (true);
}				/* fadeOut */

void
down6db (Session * this)
{
  if (this && this->data)
    {
      int i;
      int n = this->frames * this->channels;

      for (i = 0; i < n; i++)
	this->data[i] /= 2;
    }
  return;
}				/* down6db */

bool
soxEcho (Session * this, int delay)
{
  int i;
  int status;
  pid_t cpid;
  pid_t w;
  SNDFILE *sndf;
  SF_INFO sfinfo;
  static char file1wav[256];
  static char file2wav[256];
  FILE *rf;

  sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
  sfinfo.samplerate = this->samplerate;
  sfinfo.channels = this->channels;
  sprintf (file1wav, "%s/f%dj.wav", tempdir, (int) getpid ());
  sndf = sf_open (file1wav, SFM_WRITE, &sfinfo);
  if (sf_error (sndf))
    {
      puts ("Error opening the write file.");
      return (true);
    }
  i = sf_writef_short (sndf, this->data, this->frames);
  if (i != this->frames || sf_error (sndf))
    {
      puts ("Error writing the file.");
      return (true);
    }
  sf_close (sndf);
  if (verbosity > 1)
    {
      printf ("Echoing, ");
      fflush (stdout);
    }
  sprintf (file2wav, "%s/f%dk.wav", tempdir, (int) getpid ());
  cpid = fork ();
  if (cpid == 0)
    {
      rf = freopen ("/dev/null", "w", stdout);
      rf = freopen ("/dev/null", "w", stderr);
      execlp ("nice", "nice", "sox", "-v0.7", file1wav, file2wav, "echo",
	      "0.9", "0.8", itoa (delay), "0.4", (char *) NULL);
    }
  else
    {
      status = 0;
      while (true)
	{
	  w = waitpid (cpid, &status, WNOHANG);
	  if (w == cpid && WIFEXITED (status))
	    break;
	}			/* end while */
    }				/* end else */
  if (verbosity > 1)
    puts ("done.");
  unlink (file1wav);
  sfinfo.format = 0;
  sndf = sf_open (file2wav, SFM_READ, &sfinfo);
  if (sf_error (sndf))
    {
      puts ("Error opening the read file.");
      return (true);
    }
  this->samplerate = sfinfo.samplerate;
  this->channels = sfinfo.channels;
  this->frames = sfinfo.frames;
  this->data =
    (short *) x_realloc (this->data,
			 (this->frames * this->channels + 1) *
			 sizeof (short));
  i = sf_readf_short (sndf, this->data, this->frames);
  if (i != this->frames || sf_error (sndf))
    {
      puts ("Error reading the file.");
      return (true);
    }
  sf_close (sndf);
  unlink (file2wav);
  setBlocks (this, this->millisecs, 0);
  amplify (this, 1, this->blocks, soundlevel);
  return (false);
}				/* soxEcho */

int
realrate (int n)
{

  switch (n)
    {
    case 6:
    case 8:
    case 16:
    case 32:
    case 48:
      n *= 1000;
      break;
    case 11:
    case 22:
    case 44:
      n = 11025 * (n / 11);
      break;
    default:
      break;
    }
  return (n);
}				/* realrate */
