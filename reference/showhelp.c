/* showhelp.c -- Edway Audio Editor 
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

extern char *rsfx[], *wsfx[], *helpername[];
extern char *cmd[];
extern bool helperstatus[];

void
show1help (char *arg)
{
  char buf[256];
  int i;
  int rv;

  if (arg[0] == '-')
    sprintf (buf, "cat %s/HELP/d%s", progdir, arg);
  else if (!strchr (arg, '-'))
    sprintf (buf, "cat %s/HELP/c-%s", progdir, arg);
  else
    sprintf (buf, "cat %s/HELP/%s", progdir, arg);
  rv = system (buf);
  if (!strcmp (arg, "h"))
    {
      printf ("Help is available on these %d commands and options:\n",
	      c_enums);
      for (i = 0; i < c_enums; i++)
	if (i % 12)
	  printf (", %4s", cmd[i]);
	else
	  printf ("\n%5s", cmd[i]);
      puts ("");
      return;
    }
  if (!strcmp (arg, "r"))
    {
      printf ("These are the %d readible file suffixes:\n", r_enums);
      for (i = 1; i < r_enums; i++)
	if ((i % 10) != 1)
	  printf (", %5s", rsfx[i]);
	else
	  printf ("\n%6s", rsfx[i]);
      puts ("");
      return;
    }
  if (!strcmp (arg, "w"))
    {
      printf ("These are the %d writable file suffixes: \n", w_enums);
      for (i = 0; i < w_enums; i++)
	if (i % 10)
	  printf (", %5s", wsfx[i]);
	else
	  printf ("\n%6s", wsfx[i]);
      puts ("");
      return;
    }
  return;
}				/* show1help */

void
show2help (char *arg)
{
  char *browser, buf[256];
  int i;
  int rv;

  if (arg && strlen (arg))
    {
      for (i = 0; i < c_enums; i++)
	if (!strcmp (cmd[i], arg))
	  break;
      switch (i)
	{
	case c_bang:
	  show1help ("c-bang");
	  return;
	case c_slash:
	  show1help ("c-slash");
	  return;
	case c_eq:
	  show1help ("c-eq");
	  return;
	case c_qm:
	  show1help ("c-qm");
	  return;
	case c_qmqm:
	  show1help ("c-qmqm");
	  return;
	default:
	  if (i < c_enums)
	    {
	      show1help (arg);
	      return;
	    }
	  printf ("\"%s\" is not recognized.\n", arg);
	  puts ("Type \"h h\" for help with the h command.");
	  printf
	    ("\nEdway uses these %d helper programs for some functions:\n",
	     h_enums);
	  for (i = 0; i < h_enums; i++)
	    if (i % 5)
	      printf (", %8s (%d)", helpername[i], helperstatus[i]);
	    else
	      printf ("\n%9s (%d)", helpername[i], helperstatus[i]);
	  puts ("");
	}			/* end switch */
      return;
    }
  if (!getenv ("BROWSER"))
    {
      if (lookfor ("lynx"))
	browser = xstrdup ("lynx");
      else
	{
	  fputs ("No BROWSER available.", stderr);
	  return;
	}
    }
  else
    browser = xstrdup (getenv ("BROWSER"));
  sprintf (buf, "%s %s/manual.html", browser, progdir);
  rv = system (buf);
  return;
}				/* show2help */
