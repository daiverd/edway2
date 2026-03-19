/* edway.h -- Edway Audio Editor 
  * 
Copyright (c) 2009-2010, Charles E. Hallenbeck, Ph.D., chuckh@ftml.net
*
  *  This software is offered under the terms of the GNU General Public License
  *  as described in the file "COPYING" included with the software. Please read
  *  the terms and conditions of the GPL before using this software.
  * 
  */

#include <stdlib.h>
#include <stdio.h>
#include <sndfile.h>
#include <unistd.h>
#include <string.h>
#include <sys/wait.h>
#include <pwd.h>
#include <sys/stat.h>
#include <termios.h>
#include <readline/readline.h>
#include <readline/history.h>
#include <math.h>
#include <limits.h>
#include <sched.h>
#include <errno.h>
#include <alsa/asoundlib.h>
#include <sys/time.h>
#include <signal.h>

#define VERSION "0.2"
#define REVISION "13"
#define PEAKMAX 32440.32
#define KB 1024
#define MB 1048576
#define TICK '\''
#define MS_PER_MINUTE 60000
#define MS_PER_HOUR 3600000
#define true 1
#define false 0
#define SOXVER "sox: SoX v14.3.0"

#define ZX 5
#define NBARS 385
#define OGGQUAL 3.0
/* Caution: DRCUT is 2.0 / DRTAIL, while DRLEN is independent. */
#define DRTAIL 0.07
#define DRLEN 0.70710678
#define DRCUT 28.571428
/* format statements */
#define FM01 "nice ffmpeg 2>/dev/null -i %s -ab %dK -f rm %s"
#define FM02 "nice lame --silent -b %d %s \"%s\""
#define FM03 "nice flac --lax -s -f -o \"%s\" %s"
#define FM04 "nice ffmpeg 2>/dev/null -i %s -ab 4.75k -ac 1 -ar 8000 %s"
#define FM07 "nice faac -q 100 -o \"%s\" %s >/dev/null 2>&1"
#define FM09 "nice speexenc 1>/dev/null 2>&1 %s --vbr --vad %s \"%s\""
#define FM11 "nice sox %s -tcdr -r44100 -2 -s -c2 %s"
#define FM12 "I can't find \"%s\", is it installed?"
#define FM16 "nice oggenc -Q -q %0.2f -o \"%s\" %s"
#define FM17 "nice wavpack -q -r %s -o %s"

/* typedefs, structs, and enums */
typedef unsigned char bool;
typedef unsigned short unshort;
typedef struct Lines
{
  struct Lines *next;
  char *line;
} Lines;

typedef struct List
{
  struct List *next, *prev;
  char *name;
  char type[6];
  time_t age;
  short sfx;
} List;

typedef struct Digest
{
  struct Digest *next;
  char *name;
  int max, size;
  long int mark;
  long int time;
} Digest;

typedef struct Session
{
  struct Session *next;
  struct Session *prev;
  short *data;
  short number;
  short rsfx;
  short wsfx;
  short zfactor;
  int size;
  int frames;
  int blocksize;
  int blocks;
  int channels;
  int samplerate;
  int savedrate;
  int point;
  int millisecs;
  long int mark[26];
  double bstart;
  double bstop;
  char *label;
  char *source;
  char *target;
  bool clean;
  bool empty;
} Session;

typedef struct StereoBars
{
  int ch1bar[NBARS], ch2bar[NBARS];
} StereoBars;

typedef struct StereoStats
{
  double chancorr;
  double c1db;
  double c2db;
  int c1max;
  int c1min;
  int c2max;
  int c2min;
  int c1dc;
  int c2dc;
} StereoStats;

typedef struct MonoStats
{
  double db;
  int max;
  int min;
  int dc;
  int rms;
  int rms7;
  int rms93;
} MonoStats;

typedef struct Command
{
  int address1, address2, address3, number;
  char *cmd, *arg;
} Command;

enum				/* readable file types by suffix */
{ r_0, r_3gp, r_aac, r_amr, r_asf, r_avi, r_cdr, r_flv, r_m4a, r_m4v, r_mid,
  r_mod, r_mov, r_mp3, r_mp4, r_mpeg, r_mpg, r_ogg, r_ogv, r_ra, r_raw, r_rm,
  r_spx, r_swf, r_txt, r_trv, r_wav, r_wma, r_wmv, r_wv, r_enums
};
enum				/* writable file types by suffix */
{ w_3gp, w_aac, w_aiff, w_amr, w_au, w_cdr, w_flac, w_gsm, w_m4a, w_mp3,
  w_null, w_ogg, w_rm, w_spx, w_trv, w_trw, w_wav, w_wv, w_enums
};
enum				/* helper programs */
{ arecord, faac, faad, flac, lame, ffmpeg, mplayer, oggdec, oggenc, sox,
  speexdec,
  speexenc,
  swift, timidity, tts, wavpack, h_enums
};
enum				/* commands and options */
{ c_bang, c_slash, c_eq, c_qm, c_qmqm, c_b, c_bpf, c_cap, c_cs, c_d, c_db,
  c_e, c_ek, c_f, c_fi, c_fo, c_ft, c_g, c_gen, c_h, c_hg, c_hpf, c_j, c_k,
  c_l, c_lpf, c_m, c_ms, c_mx, c_nb, c_nc, c_oq, c_p, c_pub, c_q, c_qt, c_r,
  c_rb, c_sl, c_sm, c_sq, c_sr, c_t, c_u, c_uv, c_v, c_vs, c_w, c_z, c_zap,
  d_a, d_b, d_c, d_d, d_e, d_f, d_h, d_i, d_l, d_n, d_o, d_p, d_q, d_r, d_t,
  d_V, d_v, d_w, d_z, c_enums
};
enum				/* sox filter types */
{
  unf, bpf, hpf, lpf
};
enum				/* shapes of generated audio */
{ flat, sine, square, sawtooth };
