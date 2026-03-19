/* extras.c -- Edway Audio Editor 
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

extern char *configdir;
extern bool verbosity;
extern char *playlistdir;
extern char *playDevice;
extern char *captureDevice;
extern bool quietflag;
extern bool ignore;

static Digest *dhead;

snd_output_t *output = NULL;

int
playBlocks (Session * this, long int b1, long int b2)
{
  int err;
  snd_pcm_sframes_t f1, f2, delta1, delta2;
  snd_pcm_sframes_t frames = 0;
  snd_pcm_t *handle;
  short *data;

  if (this->samplerate < 5000 || this->samplerate > 50000)
    {
      printf ("sample rate %d out of bounds.\n", this->samplerate);
      return (b1);
    }
  if (verbosity > 1)
    printf ("%ld, %ld.\n", b1, b2);
  f1 = (b1 < 1 ? 0 : this->blocksize * (b1 - 1));
  f2 = (b2 < 1 ? this->blocksize : this->blocksize * b2);
  delta1 = this->samplerate * this->channels / 4;	/* 0.25 second */
  delta2 = (delta1 * this->channels);

  if ((err =
       snd_pcm_open (&handle, playDevice, SND_PCM_STREAM_PLAYBACK, 0)) < 0)
    {
      printf ("Playback open error: %s\n", snd_strerror (err));
      return (EXIT_FAILURE);
    }
  data = this->data + f1 * this->channels;

  if ((err =
       snd_pcm_set_params (handle,
			   SND_PCM_FORMAT_S16_LE,
			   SND_PCM_ACCESS_RW_INTERLEAVED,
			   this->channels, this->samplerate, true,
			   500000)) < 0)
    {				/* 0.5 second */
      printf ("Playback open error: %s\n", snd_strerror (err));
      return (EXIT_FAILURE);
    }

  while (f1 < f2)
    {
      if (delta1 > f2 - f1)
	delta1 = f2 - f1;
      frames = snd_pcm_writei (handle, data, delta1);
      if (frames < 0)
	frames = snd_pcm_recover (handle, frames, 0);
      if (frames < 0)
	{
	  printf ("snd_pcm_writei failed: %s\n", snd_strerror (err));
	  break;
	}
      f1 += delta1;
      data += delta2;
      if (getch () >= SPACE)
	f2 = f1;
    }

  if (frames > 0 && (long) frames < (long) delta1)
    printf ("Short write (expected %li, wrote %li)\n", (long) delta1, frames);
  snd_pcm_drain (handle);
  snd_pcm_close (handle);
  return (f1 / this->blocksize);
}				/* playBlocks */

int
playfile (Session * this)
{
  int err;
  snd_pcm_sframes_t f1 = 0, f2 = 0, delta;
  snd_pcm_sframes_t frames = 0;
  snd_pcm_t *handle;
  short *data, *pause;
  Digest *temp = NULL, *ours = NULL;
  struct stat fs;
  int s6, s60, s600;
  int key = 'x';
  char *cmd = NULL;
  char *ch;
  bool pausing = false;
  bool writing = false;
  char file1txt[256];
  FILE *fout;
  int rv;

  if (!this)
    {
      puts ("No file to play.");
      return (EXIT_FAILURE);
    }
  if (this->samplerate < 5000 || this->samplerate > 50000)
    {
      printf ("sample rate %d out of bounds.\n", this->samplerate);
      return (EXIT_FAILURE);
    }

  if ((ch = strrchr (this->source, '/')))
    ch++;
  else
    ch = this->source;
  if (verbosity)
    {
      printf ("%s, %s\n", ch, playtime (this, 100));
      sleep (3);
    }

  if (!stat (this->source, &fs))
    {
      ours = (Digest *) xmalloc (sizeof (Digest));
      ours->max = this->frames;
      ours->size = fs.st_size;
      ours->time = fs.st_mtime;
      ours->name = xstrdup (ch);
      getHistory ();
      for (temp = dhead; temp; temp = temp->next)
	{
	  if (temp->max && ours->size == temp->size
	      && ours->time == temp->time && !strcmp (temp->name, ours->name))
	    f1 = ((1.0 * temp->mark) / (1.0 * temp->max)) * this->frames;
	}
    }

  if (f1)
    {
      double x = (1.0 * f1) / this->samplerate;
      int n = (int) x / 60;
      x -= n * 60;
      writing = true;
      printf ("Bookmarked at %0dM%0.02f0, %0.02f%%, ", n, x,
	      (100.0 * f1) / this->frames);
      while (!(cmd = readline ("type R to resume from there: ")));
      if (cmd[0])
	key = tolower (cmd[0]);
      free (cmd);
      cmd = NULL;
      if (!strchr ("npqr", key))
	f1 = 0;
    }

  if (!strchr ("npq", key))
    {
      f2 = this->frames;
      delta = this->samplerate * this->channels / 4;	/* 0.25 second */
      data = this->data + f1 * this->channels;
      pause = (short *) xcalloc (delta * this->channels, sizeof (short));
      s6 = this->samplerate * 6;
      s60 = s6 * 10;
      s600 = s6 * 100;

      if ((err =
	   snd_pcm_open (&handle, playDevice, SND_PCM_STREAM_PLAYBACK,
			 0)) < 0)
	{
	  printf ("Playback open error: %s\n", snd_strerror (err));
	  return (EXIT_FAILURE);
	}

      if ((err =
	   snd_pcm_set_params (handle,
			       SND_PCM_FORMAT_S16_LE,
			       SND_PCM_ACCESS_RW_INTERLEAVED,
			       this->channels, this->samplerate, true,
			       500000)) < 0)
	{			/* 0.5 second */
	  printf ("Playback open error: %s\n", snd_strerror (err));
	  return (EXIT_FAILURE);
	}

      if (quietflag)
	rv = system ("echo \".\" > /var/tmp/quiet.edway");

      while (f1 < f2)
	{
	  if (pausing)
	    snd_pcm_writei (handle, pause, delta);
	  else
	    {
	      if (f1 < 1)
		f1 = 0;
	      data = this->data + f1 * this->channels;
	      if (delta > f2 - f1)
		delta = f2 - f1;
	      frames = snd_pcm_writei (handle, data, delta);
	      if (frames < 0)
		frames = snd_pcm_recover (handle, frames, 0);
	      if (frames < 0)
		{
		  printf ("snd_pcm_writei failed: %s\n", snd_strerror (err));
		  break;
		}
	    }
	  if ((key = getch ()) == SPACE)
	    pausing = (pausing ? false : true);
	  else if (key == '.')
	    printf (" %0.02f%%\n", (100.0 * f1) / f2);
	  else if (key == ',')
	    {
	      double x = (1.0 * f1) / this->samplerate;
	      int n = (int) x / 60;
	      x -= n * 60;
	      printf (" %0dM%0.02f0.\n", n, x);
	    }
	  else if (strchr ("npq", key))
	    f2 = f1;
	  if (pausing)
	    continue;
	  switch (key)
	    {			/* navigation commands */
	    case 'b':
	      f1 -= s6;
	      break;
	    case 'B':
	      f1 -= s60;
	      break;
	    case '<':
	      f1 -= s600;
	      break;
	    case '[':
	      f1 = 0;
	      break;
	    case 'f':
	      f1 += s6;
	      break;
	    case 'F':
	      f1 += s60;
	      break;
	    case '>':
	      f1 += s600;
	      break;
	    case ']':
	      if (f2 - s6 < f1)
		f1 = f2;
	      else
		f1 = f2 - s6;
	      break;
	    default:
	      f1 += delta;
	    }			/* switch */
	}
      if (quietflag)
	unlink ("/var/tmp/quiet.edway");
      if (frames > 0 && (long) frames < (long) delta)
	printf ("Short write (expected %li, wrote %li)\n", (long) delta,
		frames);
      snd_pcm_drain (handle);
      snd_pcm_close (handle);
      free (pause);
    }
  if (ignore == false)
    {
      ours->mark = f1;
      getHistory ();
      for (temp = dhead; temp; temp = temp->next)
	if (temp->max && ours->size == temp->size && ours->time == temp->time
	    && !strcmp (temp->name, ours->name))
	  {
	    writing = true;
	    temp->mark = 0;
	    temp->max = 0;
	    temp->size = 0;
	    temp->time = 0;
	    free (temp->name);
	    temp->name = NULL;
	  }
      if (writing || strchr ("nq", key))
	{
	  int n = 0;

	  sprintf (file1txt, "%s/history.edw", configdir);
	  if ((fout = fopen (file1txt, "w")))
	    {
	      if (f1 < this->frames)
		fprintf (fout, "%ld, %d, %d, %ld, %s\n", ours->mark,
			 ours->max, ours->size, (long) ours->time,
			 ours->name);
	      for (temp = dhead; temp != NULL; temp = temp->next)
		if (temp->name)
		  {
		    fprintf (fout, "%ld, %d, %d, %ld, %s\n", temp->mark,
			     temp->max, temp->size, (long) temp->time,
			     temp->name);
		    if (++n == 100)
		      break;
		  }
	      fclose (fout);
	    }
	  else
	    printf ("Cannot write %s\n", file1txt);
	  puts ("");
	}
    }
  return (key);
}				/* playfile */

void
getHistory (void)
{
  FILE *fin;
  char buf[128];
  char name[128];
  char file1txt[256];
  int i1;
  int i2;
  int j;
  long int k;
  Digest *temp;
  char *rs;

  if (ignore)
    return;
  for (temp = dhead; dhead != NULL; dhead = temp)
    {
      temp = temp->next;
      free (dhead);
    }

  sprintf (file1txt, "%s/history.edw", configdir);
  if ((fin = fopen (file1txt, "r")))
    {
      rs = fgets (buf, 128, fin);
      while (!feof (fin))
	{
	  buf[strlen (buf) - 1] = 0;
	  sscanf (buf, "%d, %d, %d, %ld, %s", &i1, &i2, &j, &k, name);
	  if (!i1 && !i2 && !j && !k)
	    break;
	  temp = (Digest *) xmalloc (sizeof (Digest));
	  temp->next = dhead;
	  dhead = temp;
	  temp->mark = i1;
	  temp->max = i2;
	  temp->size = j;
	  temp->time = k;
	  temp->name = xstrdup (name);
	  rs = fgets (buf, 128, fin);
	}
      fclose (fin);
    }
  return;
}				/* getHistory */
