/* session.c -- Edway Audio Editor 
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

extern char *configdir, *tempfile, *tempdir;
extern List *fhead, *ftail, *fnewest;
extern Session *head, *tail;
extern short verbosity;
extern bool zaptarget, zapsource;
extern bool smoothing, squeezingp;
extern int soundlevel;
extern bool ignore;
extern double chancorr, chan1db, chan2db;
extern int chan1max, chan1min, chan2max, chan2min, chan1dc, chan2dc;
extern bool public;
extern double squeezeDB;
extern int squeezeKeep;
extern double smoothTime;
extern double oggqual;
extern int smoothDrop;
extern double smoothDB;
extern int echoDelay;
extern int lowerHertz;
extern int upperHertz;
extern bool helperstatus[];
extern char *backuptext;
extern char *backupwave;
static bool autosave = true;

int
editmode (void)
{
  int i;
  int m;
  bool okay;
  char buf[256];
  List *fnext;
  Session *this = NULL;
  Session *next = NULL;
  FILE *fin;
  Command *b;
  int rv;
  char *rs;

  do				/* outer do */
    {
      if (verbosity && fnewest)
	puts ("Using newest.");

      for (fnext = fhead; fnext; fnext = fnext->next)
	if ((!fnewest || fnewest == fnext)
	    && getAudio (fnext->name, fnext->sfx, NULL) && verbosity)
	  printf ("decoding failed: %s \n", fnext->name);
      fnewest = NULL;
      zaplist ();

      if (!this)
	this = head;
      if ((b = newCommand (this)))
	{
	  if (verbosity > 2)
	    {
	      printf ("new command: |%s|\n", b->cmd);
	      printf ("b1 %d, b2 %d, b3 %d, number %d, arg %s\n", b->address1,
		      b->address2, b->address3, b->number, b->arg);
	    }

/* ch, i.e. add a chorus effect */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "ek"))
	    {
	      int n = echoDelay;

	      if (dataMissing (this))
		continue;
	      if (strlen (b->arg) && isdigit (b->arg[0]))
		n = atoi (b->arg);
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      if (soxEcho (this, n))
		puts ("sox echo failed.");
	      continue;
	    }

/* b, i.e. backup */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "b"))
	    {
	      if (!strcasecmp (b->arg, "save"))
		{
		  if (dataMissing (this))
		    continue;
		  if (saveSession (this))
		    puts ("failure while saving session.");
		  else
		    {
		      autosave = false;
		      puts ("save successful, autosave disabled.");
		    }
		}
	      else if (!strcasecmp (b->arg, "kill"))
		{
		  unlink (backupwave);
		  unlink (backuptext);
		  autosave = true;
		  puts ("kill successful, autosave enabled.");
		}
	      else
		{
		  struct stat fs;
		  bool f1 = false, f2 = false;

		  if (!stat (backupwave, &fs))
		    f1 = true;
		  if (!stat (backuptext, &fs))
		    f2 = true;
		  if (f1 && f2)
		    puts
		      ("backup available: \"b kill\" to delete it, \"u\" to recover it.");
		  else if (f1 || f2)
		    puts ("corrupted backup: might as well do \"b kill\"");
		  else
		    puts ("no backup available: \"b save\" to create one.");
		  if (autosave)
		    printf ("autosave %sabled.\n",
			    (char *) (autosave ? "en" : "dis"));
		}
	      continue;
	    }

/* u, i.e. undo */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "u"))
	    {
	      if (!this)
		this = newSession (0);
	      if (loadSession (this))
		puts ("Unable to restore session.");
	      else
		puts ("session restored ok.");
	      continue;
	    }

/* mx, i.e., mix audio from another session */
	  if (!strcasecmp (b->cmd, "mx"))
	    {
	      char *ch;
	      double infade = 0.1;
	      double outfade = 0.1;

	      if (dataMissing (this))
		continue;
	      if (!b->number)
		{
		  fputs ("Missing session number.\n", stderr);
		  continue;
		}
	      if (b->number == this->number)
		{
		  fprintf (stderr, "You are already in session #%d.\n",
			   b->number);
		  continue;
		}
	      if (strlen (b->arg) && isdigit (b->arg[0]))
		{
		  infade = outfade = atof (b->arg);
		  if ((ch = strchr (b->arg, SPACE)) && isdigit (ch[1]))
		    outfade = atof (ch + 1);
		}
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      if (combineAudio
		  (this, b->address1, b->address2, b->number, infade,
		   outfade))
		puts ("failure mixing audio.");
	      else
		puts ("audio mixed okay.");
	      continue;
	    }

/* p, i.e. play */
	  if (!strcmp (b->cmd, "/") || !strcasecmp (b->cmd, "p")
	      || !strlen (b->cmd))
	    {
	      int b1;
	      int b2;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      b1 = (!b->address1 ? this->point : b->address1);
	      b2 = (!b->address2 ? b1 : b->address2);
	      if (badRange (b1, b2))
		continue;
	      if (strcmp (b->cmd, "/"))
		this->point = playBlocks (this, b1, b2);
	      else
		this->point = b2;
	      continue;
	    }

/* question mark */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcmp (b->cmd, "?"))
	    {
	      double millisec;
	      double seconds = 0;
	      int minutes = 0;
	      int hours = 0;

	      if (dataMissing (this))
		continue;
	      if (this->target)
		{
		  millisec = (1000.0 * this->frames) / this->samplerate;
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
		  if (!strcmp (this->source, this->target))
		    printf ("file: %s\n", this->source);
		  else
		    {
		      if (verbosity > 1)
			printf ("source: %s\n", this->source);
		      printf ("target: %s\n", this->target);
		    }
		  printf ("time ");
		  if (hours)
		    printf ("%dH", hours);
		  printf ("%dM%.03f, (%d", minutes, seconds,
			  this->samplerate);
		  if (this->samplerate != this->savedrate)
		    printf ("/%d", this->savedrate);
		  printf (" %s)",
			  (char *) (this->channels == 1 ? "mono" : "stereo"));
		  printf (" %d * %d ms blocks.\n", this->blocks,
			  this->millisecs);
		}
	      else
		printf ("No file.");
	      continue;
	    }

/* double question mark */
	  if (!b->address1 && !b->address2 && !b->address3 && !strlen (b->arg)
	      && !strcmp (b->cmd, "??"))
	    {
	      Session *temp;
	      int n;
	      int sum;

	      if (dataMissing (this))
		continue;
	      sum = memsize (this);
	      printf ("This session, %s, %s memory.\n",
		      (char *) (this->label ? this->label : "unlabeled"),
		      memchars (sum));
	      if (head != tail)
		for (temp = head; temp; temp = temp->next)
		  if (temp != this)
		    {
		      n = memsize (temp);
		      sum += n;
		      printf ("Session #%d, %s, %s memory.\n",
			      temp->number,
			      (char *) (this->label ? this->
					label : "unlabeled"), memchars (n));
		    }
	      printf ("\nTotal memory, all sessions, %s.\n", memchars (sum));
	      continue;
	    }

/* l, i.e. label a session */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcmp (b->cmd, "l"))
	    {
	      if (!this && dataMissing (this))
		continue;
	      if (strlen (b->arg))
		{
		  if (this->label)
		    free (this->label), this->label = NULL;
		  if (strcmp (b->arg, "-"))
		    this->label = xstrdup (b->arg);
		}
	      printf ("%s\n",
		      (char *) (this->label ? this->label : "unlabeled"));
	      continue;
	    }

/* fi, i.e. fade in */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcmp (b->cmd, "fi"))
	    {
	      double area = 1.0;
	      double max;

	      if (dataMissing (this))
		continue;
	      max = this->frames / (1.0 * this->samplerate);
	      if (strlen (b->arg) && isdigit (b->arg[0]))
		area = atof (b->arg);
	      if (area < 0.001 || area > max)
		fprintf (stderr,
			 "Bad value %.03f: must be between 0.001 and %.03f\n",
			 area, max);
	      else
		{
		  if (autosave && saveSession (this))
		    puts ("failure saving session.");
		  if (fadeIn (this, area))
		    puts ("faded in.");
		}
	      continue;
	    }

/* fo, i.e. fade out */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcmp (b->cmd, "fo"))
	    {
	      double area = 1.0;
	      double max;

	      if (dataMissing (this))
		continue;
	      max = this->frames / (1.0 * this->samplerate);
	      if (strlen (b->arg) && isdigit (b->arg[0]))
		area = atof (b->arg);
	      if (area < 0.001 || area > max)
		fprintf (stderr,
			 "Bad value %.03f: must be between 0.001 and %.03f\n",
			 area, max);
	      else
		{
		  if (autosave && saveSession (this))
		    puts ("failure saving session.");
		  if (fadeOut (this, area))
		    puts ("faded out.");
		}
	      continue;
	    }

/* j, i.e., join two edit sessions */
	  if (!b->address2 && !b->address3 && b->number && !strlen (b->arg)
	      && !strcasecmp (b->cmd, "j"))
	    {
	      if (dataMissing (this))
		continue;
	      if (b->number == this->number)
		{
		  printf ("You are already in session #%d.\n", this->number);
		  continue;
		}
	      joinSession (this, b->number);
	      continue;
	    }

/* k, i.e. set a mark from a to z */
	  if (b->cmd[0] == 'k' && islower (b->cmd[1]))
	    {
	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      if (b->address1)
		this->point = b->address1;
	      i = b->cmd[1];
	      i -= 'a';
	      this->mark[i] =
		(this->point - 1) * this->blocksize + 1 + this->blocksize / 2;
	      printf ("mark %c set to %d\n", b->cmd[1], this->point);
	      continue;
	    }

/* w, i.e. write to a file or buffer */
	  if (!b->address3 && !strcasecmp (b->cmd, "w"))
	    {
	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      if (b->address1)
		{
		  i = (b->address1 - 1) * this->blocksize;
		  this->bstart = (1.0 * i) / this->frames;
		}
	      else
		this->bstart = 0;
	      if (b->address2)
		{
		  i = b->address2 * this->blocksize;
		  this->bstop = (1.0 * i) / this->frames;
		}
	      else
		this->bstop = 1.0;
	      if (b->number)
		{
		  if (b->number == this->number)
		    {
		      printf ("You are already in session #%d.\n",
			      this->number);
		      continue;
		    }
		  putSession (this, b->number);
		}
	      else
		{
		  if (strlen (b->arg) && setName (this, b->arg))
		    {
		      puts ("Sorry, can't do that, name unchanged.");
		      printf ("File name %s\n", this->target);
		    }
		  putAudio (this, 0, this->savedrate);
		}
	      continue;
	    }

/* z, i.e. display multiple blocks */
	  if (!b->address2 && !b->address3 && !strlen (b->arg)
	      && !strcasecmp (b->cmd, "z"))
	    {
	      int b1;
	      int b2;
	      int i;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      if (b->number >= 1)
		this->zfactor = b->number;
	      if (b->address1)
		this->point = b->address1;
	      b1 = this->point;
	      if (!b->address1 && this->point > 1
		  && this->point < this->blocks)
		b1++;
	      i = 1;
	      if (1000 > this->millisecs)
		i = 0.5 + 1000.0 / this->millisecs;
	      b2 = b1 + i * this->zfactor - 1;
	      if (b2 > this->blocks)
		b2 = this->blocks;
	      this->point = playBlocks (this, b1, b2);
	      continue;
	    }

/* h, i.e. help */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcmp (b->cmd, "h"))
	    {
	      show2help (b->arg);
	      continue;
	    }

/* equals, i.e. tell block number */
	  if (!strcmp (b->cmd, "="))
	    {
	      if (dataMissing (this))
		continue;
	      if (!b->address2 && !strlen (b->arg))
		{
		  if (b->address1)
		    printf ("%d.\n", b->address1);
		  else
		    printf ("%d.\n", (int) (this ? this->blocks : 0));
		  continue;
		}
	    }

/* q, quit, i.e. kill session, or program if no sessions */
	  if (!strcasecmp (b->cmd, "q"))
	    {
	      if (!b->address1 && !b->address2 && !strlen (b->arg))
		{
		  if (!head)
		    break;
		  zapSession (this);
		  this = delSession (this);
		  continue;
		}
	    }

/* qt, exit, i.e. unconditional bailout */
	  if (!strcasecmp (b->cmd, "qt") || !strcasecmp (b->cmd, "exit"))
	    {
	      while (this)
		{
		  zapSession (this);
		  this = delSession (this);
		}
	      break;
	    }

/* uv, unverbose, i.e. lower the verbosity level */
	  if (!strcmp (b->cmd, "uv") || !strcmp (b->cmd, "unverbose"))
	    {
	      if (verbosity)
		verbosity--;
	      printf ("%d.\n", verbosity);
	      continue;
	    }

/* v, verbose, i.e. raise the verbosity level */
	  if (!strcmp (b->cmd, "v"))
	    {
	      printf ("%d.\n", ++verbosity);
	      continue;
	    }

	  /* exclamation, i.e. launch the shell */
	  if (!strcmp (b->cmd, "!"))
	    {
	      strcpy (buf, "/bin/sh -i");
	      if (strlen (b->arg))
		strcpy (buf, b->arg);
	      else
		puts ("Type exit when done.");
	      rv = system (buf);
	      puts ("");
	      continue;
	    }

/* e, i.e. report session number, or switch sessions */
	  if (!b->address1 && !b->address2 && !b->address3 && !strlen (b->arg)
	      && !strcasecmp (b->cmd, "e"))
	    {
	      if (this && this->number == b->number)
		{
		  printf ("You are already in session #%d.\n", b->number);
		  continue;
		}
	      if (b->number)
		{
		  for (next = head; next; next = next->next)
		    if (next->number == b->number)
		      break;
		  if (next)
		    {
		      this = next;
		      puts ((this->target ? this->target : "no file"));
		    }
		  else
		    {
		      this = newSession (b->number);
		      puts ("new session.");
		    }
		  continue;
		}
	      if (this)
		printf ("session #%d, %s\n", this->number,
			(this->target ? this->target : "no file"));
	      else
		puts ("no session exists.");
	      continue;
	    }

/* r, i.e. read from a file with wildcards */
	  if (!b->address1 && !b->address2 && !b->address3 && !b->number
	      && (!strcasecmp (b->cmd, "e") || !strcasecmp (b->cmd, "r")))
	    {
	      if (strlen (b->arg))
		{
		  okay = !strchr (b->arg, '*') && !strchr (b->arg, '?');
		  sprintf (buf, "%s %s > %s",
			   (okay ? "echo" : "ls -1"), b->arg, tempfile);
		  if (verbosity > 2)
		    puts (buf);
		  rv = system (buf);
		  sprintf (buf, "sed -i -r \"s/ +/\\n/g\" %s", tempfile);
		  if (verbosity > 2)
		    puts (buf);
		  rv = system (buf);
		  m = 0;
		  fin = fopen (tempfile, "r");
		  rs = fgets (buf, 256, fin);
		  while (!feof (fin))
		    {
		      buf[strlen (buf) - 1] = 0;
		      if (strlen (buf) < 4)
			m = 0;
		      if (m == 0 && strlen (buf) > 3)
			{
			  if (buf[strlen (buf) - 1] == ':')
			    {
			      m = 1;
			      buf[strlen (buf) - 1] = 0;
			    }
			  add2list (buf);
			}
		      rs = fgets (buf, 256, fin);
		    }		/* end while */
		  fclose (fin);
		  unlink (tempfile);
		  for (i = 0, fnext = fhead; fnext != NULL;
		       fnext = fnext->next)
		    i++;
		  if (verbosity && i > 1)
		    printf ("Found %d files.\n", i);
		}
	      else
		puts ("no file specified.");
	      continue;
	    }

/* r<n>, i.e. read data from session #n */
	  if (!b->address2 && !b->address3 && b->number && !strlen (b->arg)
	      && !strcasecmp (b->cmd, "r"))
	    {
	      int b1 = 0;

	      if (this)
		{
		  if (b->number == this->number)
		    {
		      printf ("You are already in session #%d.\n",
			      this->number);
		      continue;
		    }
		  if (outOfBounds
		      (this, b->address1, b->address2, b->address3))
		    continue;
		  b1 = (!b->address1 ? this->point : b->address1);
		  b1 = (b->address1 > this->blocks ? this->blocks : b1);
		}
	      getSession (this, b->number, b1);
	      continue;
	    }

/* m, i.e. move blocks within the session */
	  if (!strcasecmp (b->cmd, "m"))
	    {
	      int b1;
	      int b2;
	      int b3;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      b1 = (b->address1 < 1 ? this->point : b->address1);
	      b1 = (b1 > this->blocks ? this->blocks : b1);
	      b2 = (b->address2 < 1 ? b1 : b->address2);
	      b2 = (b2 > this->blocks ? this->blocks : b2);
	      b3 = (b->address3 < 1 ? this->point : b->address3);
	      b3 = (b3 > this->blocks ? this->blocks : b3);
	      if (badRange (b1, b2))
		continue;
	      if (b3 >= b1 - 1 && b3 <= b2)
		puts ("destination and range overlap.");
	      else
		moveBlocks (this, b1, b2, b3);
	      continue;
	    }

/* d, i.e. delete blocks */
	  if (!b->address3 && !strlen (b->arg) && !strcasecmp (b->cmd, "d"))
	    {
	      int b1;
	      int b2;
	      int i;
	      int j;
	      int n1;
	      int n2;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      b1 = (b->address1 ? b->address1 : this->point);
	      b2 = (b->address2 ? b->address2 : b1);
	      b2 = (b->address2 > this->blocks ? this->blocks : b2);
	      if (badRange (b1, b2))
		continue;
	      i = this->blocksize * (b1 - 1);
	      j = this->blocksize * b2;
	      if ((this->frames - j) < this->blocksize)
		j = this->frames;
	      i *= this->channels;
	      j *= this->channels;
	      n1 = this->frames * this->channels;
	      n2 = n1 + i - j;
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      if (n2 < 2 * this->samplerate * this->channels / 1000)
		{
		  zapSession (this);
		  continue;
		}
	      while (j < n1)
		this->data[i++] = this->data[j++];
	      this->data =
		(short *) realloc (this->data,
				   (n2 + this->channels) * sizeof (short));
	      this->frames = n2 / this->channels;
	      i = this->point;
	      setBlocks (this, this->millisecs, 0);
	      if (i > b2)
		i -= (1 + b2 - b1);
	      else if (i > b1)
		i = b1;
	      if (i > this->blocks)
		this->point = this->blocks;
	      else
		this->point = i;
	      for (i = 0; i < 26; i++)
		if (this->mark[i] >= b2 * this->blocksize)
		  this->mark[i] -= ((1 + b2 - b1) * this->blocksize);
		else if (this->mark[i] >= b1 * this->blocksize)
		  this->mark[i] = 0;
	      continue;
	    }

/* rt, i.e. retain blocks */
	  if (!b->address3 && !strlen (b->arg) && !strcasecmp (b->cmd, "rb"))
	    {
	      int b1;
	      int b2;
	      int i;
	      int n1;
	      int n2;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      if (!b->address1 && !b->address2)
		{
		  puts ("Missing block addresses.");
		  continue;
		}
	      b1 = (b->address1 ? b->address1 : this->point);
	      b2 = (b->address2 ? b->address2 : b1);
	      b2 = (b->address2 > this->blocks ? this->blocks : b2);
	      if (badRange (b1, b2))
		continue;
	      n1 = this->blocksize * (b1 - 1);
	      n2 = this->blocksize * b2;
	      if ((this->frames - n2) < this->blocksize)
		n2 = this->frames;
	      n1 *= this->channels;
	      n2 *= this->channels;
	      n2 = n2 - n1 + 1;
	      if (n2 < 2 * this->samplerate * this->channels / 1000)
		{
		  zapSession (this);
		  continue;
		}
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      for (i = 0; i < n2; i++)
		this->data[i] = this->data[n1++];
	      this->data =
		(short *) realloc (this->data,
				   (n2 + this->channels) * sizeof (short));
	      this->frames = n2 / this->channels;
	      i = this->point;
	      setBlocks (this, this->millisecs, 0);
	      if (i >= b1)
		this->point = i + 1 - b1;
	      if (this->point > this->blocks)
		this->point = this->blocks;
	      for (i = 0; i < 26; i++)
		if (this->mark[i] > this->frames)
		  this->mark[i] = 0;
		else if (this->mark[i] >= b1 * this->blocksize)
		  this->mark[i] -= ((b1 - 1) * this->blocksize);
	      continue;
	    }

/* cs, i.e., report the channel statistics */
	  if (!b->address3 && !strlen (b->arg) && !strcasecmp (b->cmd, "cs"))
	    {
	      int b1;
	      int b2;
	      StereoStats *g;
	      double t;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      if (this->channels != 2)
		{
		  puts ("this isn't stereo.");
		  continue;
		}
	      b1 = (b->address1 ? b->address1 : this->point);
	      b2 = (b->address2 ? b->address2 : b1);
	      b2 = (b->address2 > this->blocks ? this->blocks : b2);
	      if (!b->address1 && !b->address2)
		{
		  b1 = 1;
		  b2 = this->blocks;
		}
	      t = (b2 - b1 + 1) * 100 / (1.0 * this->blocks);
	      if (badRange (b1, b2))
		continue;
	      if (b1 == b2)
		printf ("block %d,", b1);
	      else
		{
		  if (b1 == 1)
		    printf ("from beginning");
		  else
		    printf ("block %d", b1);
		  if (b2 == this->blocks)
		    printf (" to end,");
		  else if (b1 == 1)
		    printf (" to block %d,", b2);
		  else
		    printf (" to %d,", b2);
		}
	      g = correlate (this, b1, b2);
	      printf (" R = %.2f, %s:\n", g->chancorr, playtime (this, t));
	      printf
		("left channel %.1fdB, 		 range -%d%%, to +%d%%, DC component %d.\n",
		 g->c1db, g->c1min, g->c1max, g->c1dc);
	      printf
		("right channel %.1fdB, 		 range -%d%%, to +%d%%, DC component %d.\n",
		 g->c2db, g->c2min, g->c2max, g->c2dc);
	      continue;
	    }

/* db, i.e., report the loudness */
	  if (!b->address3 && !strcasecmp (b->cmd, "db"))
	    {
	      int b1;
	      int b2;
	      int n;
	      MonoStats *g;
	      double t;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      b1 = (b->address1 ? b->address1 : this->point);
	      b2 = (b->address2 ? b->address2 : b1);
	      b2 = (b->address2 > this->blocks ? this->blocks : b2);
	      if (!b->address1 && !b->address2)
		{
		  b1 = 1;
		  b2 = this->blocks;
		}
	      t = (b2 - b1 + 1) * 100 / (1.0 * this->blocks);
	      if (badRange (b1, b2))
		continue;
	      {
		if (strlen (b->arg))
		  {
		    n = atoi (b->arg);
		    if (n > SHRT_MAX)
		      n = SHRT_MAX;
		    else if (n < -60)
		      n = 0;
		    else if (n < 21)
		      n = db2rms (n);
		    amplify (this, b1, b2, n);
		  }
		if (b1 == b2)
		  printf ("block %d,", b1);
		else
		  {
		    if (b1 == 1)
		      printf ("from beginning");
		    else
		      printf ("block %d", b1);
		    if (b2 == this->blocks)
		      printf (" to end,");
		    else if (b1 == 1)
		      printf (" to block %d,", b2);
		    else
		      printf (" to %d,", b2);
		  }
		g = amplitude (this, b1, b2);
		printf (" %s, %.1f dB.\n", playtime (this, t), g->db);
		if (g->rms93)
		  printf
		    ("Peaks: -%d%%, to +%d%%, DC %d, dynamic range %.1f dB.\n",
		     g->min, g->max, g->dc,
		     (rms2db (g->rms93) - rms2db (g->rms7)));
		else
		  printf ("Peaks: -%d%%, to +%d%%, DC component %d.\n",
			  g->min, g->max, g->dc);
	      }
	      continue;
	    }

/* hg, i.e. construct a histogram */
	  if (!b->address3 && !strcasecmp (b->cmd, "hg"))
	    {
	      int b1;
	      int b2;
	      int i;
	      int j;
	      int k;
	      int n1;
	      int n2;
	      double s;
	      double t;
	      int *bar;
	      StereoBars *g;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      n1 = 5;
	      if (strlen (b->arg) && strcmp (b->arg, "5")
		  && strcmp (b->arg, "7") && strcmp (b->arg, "11"))
		{
		  printf ("bad argument, %s: Must be 5, 7, or 11.\n", b->arg);
		  continue;
		}
	      if (strlen (b->arg))
		n1 = atoi (b->arg);
	      n2 = NBARS / n1;
	      b1 = (b->address1 ? b->address1 : this->point);
	      b2 = (b->address2 ? b->address2 : b1);
	      b2 = (b->address2 > this->blocks ? this->blocks : b2);
	      if (!b->address1 && !b->address2)
		{
		  b1 = 1;
		  b2 = this->blocks;
		}
	      s = 100.0 / (this->blocksize * (b2 - b1 + 1));
	      t = (b2 - b1 + 1) * 100 / (1.0 * this->blocks);
	      if (badRange (b1, b2))
		continue;
	      if (this->channels == 1)
		{
		  bar = monobar (this, b1, b2);
		  if (b1 == b2)
		    printf ("block %d,", b1);
		  else
		    {
		      if (b1 == 1)
			printf ("from beginning");
		      else
			printf ("block %d", b1);
		      if (b2 == this->blocks)
			printf (" to end,");
		      else if (b1 == 1)
			printf (" to block %d,", b2);
		      else
			printf (" to %d,", b2);
		    }
		  printf (" %s:\nM: -32768,  ", playtime (this, t));
		  for (i = 0; i < n1; i++)
		    {
		      k = 0;
		      for (j = 0; j < n2; j++)
			k += bar[i * n2 + j];
		      printf (" %0.1f,", (k * s));
		    }
		  puts (" +32767.");
		}
	      else
		{
		  g = stereobar (this, b1, b2);
		  if (b1 == b2)
		    printf ("block %d,", b1);
		  else
		    {
		      if (b1 == 1)
			printf ("from beginning");
		      else
			printf ("block %d", b1);
		      if (b2 == this->blocks)
			printf (" to end,");
		      else if (b1 == 1)
			printf (" to block %d,", b2);
		      else
			printf (" to %d,", b2);
		    }
		  printf (" %s:\nL: -32768, ", playtime (this, t));
		  for (i = 0; i < n1; i++)
		    {
		      k = 0;
		      for (j = 0; j < n2; j++)
			k += g->ch1bar[i * n2 + j];
		      printf (" %0.1f,", (k * s));
		    }
		  printf (" +32767.\nR: -32768, ");
		  for (i = 0; i < n1; i++)
		    {
		      k = 0;
		      for (j = 0; j < n2; j++)
			k += g->ch2bar[i * n2 + j];
		      printf (" %0.1f,", (k * s));
		    }
		  puts (" +32767.");
		}
	      continue;
	    }

/* t, i.e. transfer (copy) blocks within the buffer */
	  if (!strcasecmp (b->cmd, "t"))
	    {
	      int b1;
	      int b2;
	      int b3;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      b1 = (b->address1 < 1 ? this->point : b->address1);
	      b1 = (b1 > this->blocks ? this->blocks : b1);
	      b2 = (b->address2 < 1 ? b1 : b->address2);
	      b2 = (b2 > this->blocks ? this->blocks : b2);
	      b3 = (b->address3 < 1 ? this->point : b->address3);
	      b3 = (b3 > this->blocks ? this->blocks : b3);
	      if (badRange (b1, b2))
		continue;
	      if (b3 >= b1 && b3 < b2)
		puts ("destination and range overlap.");
	      else
		copyBlocks (this, b1, b2, b3);
	      continue;
	    }

/* sl, i.e. soundlevel */
	  if (!strcasecmp (b->cmd, "sl"))
	    {
	      int sl;

	      if (strlen (b->arg))
		{
		  sl = atoi (b->arg);
		  if (sl < 33 || sl > PEAKMAX)
		    {
		      printf
			("bad value %d: must be between 33 and %d.\n", sl,
			 (int) PEAKMAX);
		      sl = soundlevel;
		    }
		  else
		    soundlevel = sl;
		}
	      printf ("Soundlevel 0dB = %d.\n", soundlevel);
	      continue;
	    }

/* sr, i.e. sample rate */
	  if (!strcasecmp (b->cmd, "sr"))
	    {
	      int sr = 0;

	      if (dataMissing (this))
		continue;
	      if (b->arg)
		sr = atoi (b->arg);
	      sr = realrate (sr);
	      if (sr)
		{
		  if (sr < 5000 || sr > 50000)
		    printf
		      ("bad rate, %d: must be between 5000 and 50000.\n", sr);
		  else
		    {
		      setSamplerate (this, sr);
		      this->savedrate = this->samplerate;
		    }
		}
	      if (this->samplerate == this->savedrate)
		printf ("Sample rate %d.\n", this->samplerate);
	      else
		printf ("playback rate %d, file save rate %d.\n",
			this->samplerate, this->savedrate);
	      continue;
	    }

/* nc, i.e. number of channels */
	  if (!strcasecmp (b->cmd, "nc"))
	    {
	      int nb;
	      int nc = 0;

	      if (dataMissing (this))
		continue;
	      nb = this->channels;
	      if (strlen (b->arg))
		nc = atoi (b->arg);
	      if (nc && (nc < 1 || nc > 4))
		{
		  printf
		    ("bad channel number, %d: must be between 1 and 4.\n",
		     nc);
		  puts
		    ("1 = mono, 2 = stereo, 3 = stereo-left, 4 = stereo-right.");
		}
	      else
		setChannels (this, nc);
	      if (nc < 3)
		printf ("channels %d.\n", this->channels);
	      else if (nb == 1)
		printf ("2 channels, with channel %d empty.\n",
			(nc == 3 ? 2 : 1));
	      else if (nc == 3)
		puts ("mono, from channel 1 only.");
	      else
		puts ("mono, from channel 2 only.");
	      continue;
	    }

/* fn, i.e. filename */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "f"))
	    {
	      if (dataMissing (this))
		continue;
	      if (strlen (b->arg) < 1)
		puts (this->target);
	      else
		{
		  if (setName (this, b->arg))
		    puts ("Sorry, can't do that, name unchanged.");
		  else
		    puts (this->target);
		}
	      continue;
	    }

/* sm, i.e., smooth */
	  if (!b->address3 && !strcasecmp (b->cmd, "sm"))
	    {
	      int b1;
	      int b2;
	      double x = smoothTime;
	      int n = smoothDrop;
	      double z = smoothDB;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      b1 = (b->address1 < 1 ? 1 : b->address1);
	      b2 = (b->address2 < 1 ? this->blocks : b->address2);
	      if (badRange (b1, b2))
		continue;
	      if (strlen (b->arg))
		{
		  char *ch;

		  if (isdigit (b->arg[0]))
		    x = atof (b->arg);
		  if (x < 1.0)
		    x = 1.0;
		  if ((ch = strchr (b->arg, ',')))
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
		}
	      smoothit (this, b1, b2, x, n, z);
	      continue;
	    }

/* sq, i.e., squeeze */
	  if (!b->address3 && !strcasecmp (b->cmd, "sq"))
	    {
	      int b1;
	      int b2;
	      int n = squeezeKeep;
	      double x = squeezeDB;

	      if (dataMissing (this))
		continue;
	      if (outOfBounds (this, b->address1, b->address2, b->address3))
		continue;
	      b1 = (b->address1 < 1 ? 1 : b->address1);
	      b2 = (b->address2 < 1 ? this->blocks : b->address2);
	      if (badRange (b1, b2))
		continue;
	      if (strlen (b->arg))
		{
		  char *ch;

		  if (isdigit (b->arg[0]))
		    x = atof (b->arg);
		  if ((ch = strchr (b->arg, ',')))
		    n = atoi (ch + 1);
		}
	      squeezit (this, b1, b2, x, n);
	      continue;
	    }

/* ft, i.e. file type */
	  if (!strcasecmp (b->cmd, "ft"))
	    {
	      if (dataMissing (this))
		continue;
	      if (setType (this, b->arg))
		puts ("Sorry, can't do that, type unchanged.");
	      printf ("File type %s\n", strchr (this->target, '.') + 1);
	      continue;
	    }

/* ms, i.e. milliseconds per block */
	  if (!strcasecmp (b->cmd, "ms"))
	    {
	      int ms = 0;

	      if (dataMissing (this))
		continue;
	      if (b->arg)
		ms = atoi (b->arg);
	      setBlocks (this, ms, 0);
	      continue;
	    }

/* nb, i.e. number of blocks */
	  if (!strcasecmp (b->cmd, "nb"))
	    {
	      int nb = 0;

	      if (dataMissing (this))
		continue;
	      if (b->arg)
		nb = atoi (b->arg);
	      setBlocks (this, 0, nb);
	      continue;
	    }

/* oq, i.e. ogg quality */
	  if (!strcasecmp (b->cmd, "oq"))
	    {
	      double x;

	      if (strlen (b->arg))
		{
		  x = atof (b->arg);
		  if (x >= -1.0 && x <= 10.0)
		    oggqual = x;
		  else
		    {
		      puts ("Must be from -1 to +10");
		      continue;
		    }
		}
	      printf ("ogg quality %0.2f\n", oggqual);
	      continue;
	    }

/* cap, i.e., capture a sound in a new session */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "cap"))
	    {
	      if (helperstatus[arecord])
		{
		  char *ch;
		  if (strcasecmp (b->arg, "line")
		      && strcasecmp (b->arg, "mike")
		      && strcasecmp (b->arg, "wave"))
		    {
		      while (!
			     (ch =
			      readline
			      ("press enter to continue, c to cancel: ")));
		      if (!strcasecmp (ch, "c"))
			{
			  free (ch);
			  continue;
			}
		      free (ch);
		    }
		  if (captureAudio (b->arg))
		    puts ("capture failed.");
		}
	      else
		puts ("Helper program arecord not available.");
	      continue;
	    }

/* gen, i.e., generate a sound */
	  if (!b->address2 && !b->address3
	      && (!strcasecmp (b->cmd, "g") || !strcasecmp (b->cmd, "gen")))
	    {
	      int n;
	      char *ch;
	      char *cp;
	      int len;
	      int form = flat;
	      int duty = 5;
	      int firstF = 440;
	      int secondF = 440;
	      int b1 = 0;

	      if (this && this->data)
		{
		  if (outOfBounds
		      (this, b->address1, b->address2, b->address3))
		    continue;
		  b1 = (!b->address1 ? this->point : b->address1);
		  b1 = (b->address1 > this->blocks ? this->blocks : b1);
		}

	      for (ch = b->arg; strlen (ch); ch++)
		if (*ch == ',')
		  *ch = SPACE;
	      while ((ch = strstr (b->arg, "  ")))
		strcpy (ch, ch + 1);
	      len = 1000 * atof (b->arg) + 0.5;
	      if (len < 1)
		{
		  puts ("Duration must be at least 0.001");
		  continue;
		}
	      if ((ch = strchr (b->arg, SPACE)))
		{
		  ch++;
		  if (!strncasecmp (ch, "sin", 3))
		    form = sine;
		  else if (!strncasecmp (ch, "sqw", 3))
		    form = square;
		  else if (!strncasecmp (ch, "stw", 3))
		    form = sawtooth;
		  else
		    {
		      puts ("Unrecognized wave form.");
		      continue;
		    }
		  if ((form == square || form == sawtooth) && isdigit (ch[3]))
		    {
		      n = atoi (ch + 3);
		      if (n < 1 || n > 9)
			{
			  printf
			    ("duty cycle %d: must be between 1 and 9.\n", n);
			  continue;
			}
		      duty = n;
		    }
		  ch = strchr (ch, SPACE);
		}
	      if (ch)
		{
		  ch++;
		  n = atoi (ch);
		  if (n < 20 || n > 10000)
		    {
		      printf ("rate %d: must be between 20 and 10000.\n", n);
		      continue;
		    }
		  firstF = secondF = n;
		  if ((cp = strchr (ch, ':')))
		    {
		      cp++;
		      n = atoi (cp);
		      if (n < 20 || n > 10000)
			{
			  printf
			    ("rate %d: must be between 20 and 10000.\n", n);
			  continue;
			}
		      secondF = n;
		    }
		  ch = strchr (ch, SPACE);
		}
	      if (ch)
		printf ("extra info: %s\n", ch);
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      genAudio (this, b1, len, form, duty, firstF, secondF);
	      continue;
	    }


/* bpf, i.e., band pass filter */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "bpf"))
	    {
	      int n1 = lowerHertz;
	      int n2 = upperHertz;

	      if (dataMissing (this))
		continue;
	      if (strlen (b->arg))
		{
		  char *ch;

		  if (isdigit (b->arg[0]))
		    n1 = atoi (b->arg);
		  if ((ch = strchr (b->arg, ',')))
		    n2 = atoi (ch + 1);
		}
	      if (n1 < 125)
		{
		  printf ("%d Hertz, too low.\n", n1);
		  continue;
		}
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      if (soxFilter (this, n1, n2))
		puts ("band pass filter failed.");
	      continue;
	    }

/* hpf, i.e., high pass filter */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "hpf"))
	    {
	      int n = lowerHertz;

	      if (dataMissing (this))
		continue;
	      if (strlen (b->arg) && isdigit (b->arg[0]))
		n = atoi (b->arg);
	      if (n < 125)
		{
		  printf ("%d Hertz, too low.\n", n);
		  continue;
		}
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      if (soxFilter (this, n, 0))
		puts ("high pass filter failed.");
	      continue;
	    }

/* lpf, i.e., low pass filter */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "lpf"))
	    {
	      int n = upperHertz;

	      if (dataMissing (this))
		continue;
	      if (strlen (b->arg) && isdigit (b->arg[0]))
		n = atoi (b->arg);
	      if (n < 125)
		{
		  printf ("%d Hertz, too low.\n", n);
		  continue;
		}
	      if (autosave && saveSession (this))
		puts ("failure saving session.");
	      if (soxFilter (this, 0, n))
		puts ("low pass filter failed.");
	      continue;
	    }


/* pub, i.e., toggle between public and private smoothing */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "pub"))
	    {
	      public = (public ? false : true);
	      printf ("smoothing is %s.\n",
		      (char *) (public ? "public" : "private"));
	      continue;
	    }

/* zap, i.e. empty the data from this session */
	  if (!strcasecmp (b->cmd, "zap"))
	    {
	      if (dataMissing (this))
		continue;
	      zapSession (this);
	      continue;
	    }

/* vs, i.e., variable speed */
	  if (!b->address1 && !b->address2 && !b->address3
	      && !strcasecmp (b->cmd, "vs"))
	    {
	      double x = 1.0;

	      if (dataMissing (this))
		continue;
	      if (strlen (b->arg) && isdigit (b->arg[0]))
		x = getFactor (this, b->arg);
	      if (x < 0.8 || x > 2.0)
		printf ("Bad value, %g: must be between 0.8 and 2.0\n", x);
	      else
		{
		  if (autosave && saveSession (this))
		    puts ("failure saving session.");
		  soxFactor (this, x);
		}
	      continue;
	    }

	}			/* end of newCommand */
      puts ("unknown command.");
      if (verbosity && (head == NULL || head->data == NULL))
	puts ("type h for help, or q to quit.");
    }				/* end of outer do */
  while (true);
  return (0);
}				/* editmode */

bool
dataMissing (Session * this)
{
  if (!head || !this)
    {
      puts ("No edit session.");
      return (true);
    }
  if (!this->data)
    {
      puts ("No audio available.");
      return (true);
    }
  return (false);
}				/* dataMissing */

bool
badRange (int a, int b)
{
  if (a <= b)
    return false;
  printf ("bad range: %d to %d.\n", a, b);
  return true;
}				/* badRange */

bool
outOfBounds (Session * p, int a, int b, int c)
{
  if (p->point > p->blocks || a > p->blocks || b > p->blocks || c > p->blocks)
    {
      puts ("out of bounds.");
      printf ("point %d, max %d, a %d, b %d, c %d.\n", p->point, p->blocks, a,
	      b, c);
      return true;
    }
  return false;
}				/* outOfBounds */

bool
saveSession (Session * this)
{
  FILE *fout;
  int count;
  int i;
  SNDFILE *sndf;
  SF_INFO sfinfo;

  if (ignore || this == NULL)
    return (false);
  if (this->frames > 0)
    {
      sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
      sfinfo.channels = this->channels;
      sfinfo.samplerate = this->savedrate;
      sndf = sf_open (backupwave, SFM_WRITE, &sfinfo);
      if (sf_error (sndf))
	return (true);
      count = sf_writef_short (sndf, (short *) this->data, this->frames);
      if (sf_error (sndf))
	return (true);
      sf_close (sndf);
    }
  if (!(fout = fopen (backuptext, "w")))
    return (true);
  fprintf (fout, "number %d\n", this->number);
  fprintf (fout, "source %s\n", this->source);
  fprintf (fout, "target %s\n", this->target);
  if (this->label)
    fprintf (fout, "label %s\n", this->label);
  else
    fputs ("label \"none\"\n", fout);
  fprintf (fout, "rsfx %d\n", this->rsfx);
  fprintf (fout, "wsfx %d\n", this->wsfx);
  fprintf (fout, "zfactor %d\n", this->zfactor);
  fprintf (fout, "size %d\n", this->size);
  fprintf (fout, "frames %d\n", this->frames);
  fprintf (fout, "channels %d\n", this->channels);
  fprintf (fout, "blocksize %d\n", this->blocksize);
  fprintf (fout, "blocks %d\n", this->blocks);
  fprintf (fout, "millisecs %d\n", this->millisecs);
  fprintf (fout, "samplerate %d\n", this->samplerate);
  fprintf (fout, "savedrate %d\n", this->savedrate);
  fprintf (fout, "point %d\n", this->point);
  for (i = 0; i < 26; i++)
    fprintf (fout, "mark %ld\n", this->mark[i]);
  fclose (fout);
  return (false);
}				/* saveSession */

bool
loadSession (Session * this)
{
  SNDFILE *sndf;
  SF_INFO sfinfo;
  struct stat fs;
  FILE *fin;
  char buf[256];
  char *ch;
  int i;
  int n;
  char *rs;

  if (ignore || this == NULL)
    return (false);
  if (stat (backupwave, &fs) || stat (backuptext, &fs))
    return (true);
  if (!(fin = fopen (backuptext, "r")))
    return (true);
  if (this->data)
    zapSession (this);
  i = 0;
  rs = fgets (buf, 256, fin);
  while (!feof (fin))
    {
      buf[strlen (buf) - 1] = 0;
      ch = strchr (buf, SPACE);
      if (!strncasecmp (buf, "number ", 7))
	this->number = atoi (ch + 1);
      if (!strncasecmp (buf, "source ", 7))
	this->source = xstrdup (ch + 1);
      if (!strncasecmp (buf, "target ", 7))
	this->target = xstrdup (ch + 1);
      if (!strncasecmp (buf, "label ", 6) && !strstr (buf, "\"none\""))
	this->label = xstrdup (ch + 1);
      if (!strncasecmp (buf, "rsfx ", 5))
	this->rsfx = atoi (ch + 1);
      if (!strncasecmp (buf, "wsfx ", 5))
	this->wsfx = atoi (ch + 1);
      if (!strncasecmp (buf, "zfactor ", 8))
	this->zfactor = atoi (ch + 1);
      if (!strncasecmp (buf, "size ", 5))
	this->size = atoi (ch + 1);
      if (!strncasecmp (buf, "frames ", 7))
	this->frames = atoi (ch + 1);
      if (!strncasecmp (buf, "channels ", 9))
	this->channels = atoi (ch + 1);
      if (!strncasecmp (buf, "blocksize ", 10))
	this->blocksize = atoi (ch + 1);
      if (!strncasecmp (buf, "blocks ", 7))
	this->blocks = atoi (ch + 1);
      if (!strncasecmp (buf, "millisecs ", 10))
	this->millisecs = atoi (ch + 1);
      if (!strncasecmp (buf, "samplerate ", 11))
	this->samplerate = atoi (ch + 1);
      if (!strncasecmp (buf, "savedrate ", 10))
	this->savedrate = atoi (ch + 1);
      if (!strncasecmp (buf, "point ", 6))
	this->point = atoi (ch + 1);
      if (!strncasecmp (buf, "mark ", 5))
	this->mark[i++] = atoi (ch + 1);
      rs = fgets (buf, 256, fin);
    }
  fclose (fin);
  sfinfo.format = 0;
  sndf = sf_open (backupwave, SFM_READ, &sfinfo);
  if (sf_error (sndf))
    return (true);
  if (this->samplerate != sfinfo.samplerate)
    return (true);
  if (this->channels != sfinfo.channels)
    return (true);
  if (this->frames != sfinfo.frames)
    return (true);
  this->data =
    (short *) xmalloc (sizeof (short) * sfinfo.frames * sfinfo.channels);
  n = sf_readf_short (sndf, this->data, sfinfo.frames);
  if (this->frames != n || sf_error (sndf))
    return (true);
  sf_close (sndf);
  if (autosave)
    {
      unlink (backuptext);
      unlink (backupwave);
    }
  return (false);
}				/* loadSession */
