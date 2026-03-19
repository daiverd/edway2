/* This file is machine-generated, do not hand edit. */

/* sourcefile=main.c */
int getch (void);
void *xmalloc (size_t numbytes);
char *xstrdup (const char *src);
void *x_realloc (void *mem, size_t size);
void *xcalloc (size_t nmemb, size_t size);
void catchsig (int n);
int main (int argc, char **argv);
void getconfig (void);
int readConfig (void);
void cfgError (char *buf);
void updateConfig (int n);
int cfgVersion (char *f);
int getOthers (char *arg);

/* sourcefile=players.c */
int playBlocks (Session * this, long int b1, long int b2);
int playfile (Session * this);
void getHistory (void);

/* sourcefile=reformat.c */
bool reformat (int channels0, int rate0, char *cname, char *ctype);
int getAudio (char *name, int sfx, char *cname);
int putAudio (Session * this, int channels, int rate);

/* sourcefile=session.c */
int editmode (void);
bool dataMissing (Session * this);
bool badRange (int a, int b);
bool outOfBounds (Session * p, int a, int b, int c);
bool saveSession (Session * this);
bool loadSession (Session * this);

/* sourcefile=showhelp.c */
void show1help (char *arg);
void show2help (char *arg);

/* sourcefile=support.c */
void add2list (char *fn);
int readable (char *name);
int writable (char *name);
bool lookfor (char *name);
short voxdecoder (short b3, short b2, short b1, short b0);
char voxencoder (short x1, short x2);
Session *newSession (int n);
void zaplist (void);
void zapSession (Session * this);
Session *delSession (Session * this);
char *checkname (char *oldname);
char *newname (char *dir, char *stub);
char *itoa (long n);
StereoStats *correlate (Session * this, int b1, int b2);
StereoBars *stereobar (Session * this, int b1, int b2);
double db2rms (double db);
double pearson (int n, double x, double y, double x2, double y2, double xy);
short setChannels (Session * this, int mode0);
short setSamplerate (Session * this, int rate0);
short setType (Session * this, char *type);
short setFParms (Session * this, int channels0, int rate0);
bool setName (Session * this, char *name);
void sanitize (Session * this, short level, bool normal);
double amplify (Session * this, int b1, int b2, int level);
MonoStats *amplitude (Session * this, int b1, int b2);
int *monobar (Session * this, int b1, int b2);
double rms2db (double rms);
char *playtime (Session * this, double x);
void squeezit (Session * this, int b1, int b2, int db, int keep);
void smoothit (Session * this, int b1, int b2, double span, int drop,
	       double db);
short kbps (Session * this);
Command *newCommand (Session * this);
int setBlocks (Session * this, int ms, int nb);
int getAddType (char *arg);
void putSession (Session * that, int number);
void getSession (Session * that, int number, int where);
void joinSession (Session * that, int number);
void moveBlocks (Session * this, int b1, int b2, int b3);
void copyBlocks (Session * this, int b1, int b2, int b3);
int memsize (Session * this);
char *memchars (int mem);
int soxFilter (Session * this, int lower, int upper);
int soxFactor (Session * this, double factor);
int captureAudio (char *arg);
bool genAudio (Session * that, int where, int len, int form, int duty,
	       int firstF, int secondF);
double getFactor (Session * this, char *arg);
bool combineAudio (Session * that, int b1, int b2, int num, double fade1,
		   double fade2);
bool fadeIn (Session * this, double area);
bool fadeOut (Session * this, double area);
void down6db (Session * this);
bool soxEcho (Session * this, int delay);
int realrate (int n);
