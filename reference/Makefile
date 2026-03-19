# Makefile for 'edway, an audio editor
#
VER = 0.2
REV =13
#
INSTALL = install
# Compiler and CFLAGS can be modified from the user's environment.
# name of compiler
CC = gcc
# compiler flags
CFLAGS += -O2 -Wall  
# Libraries
LIBS = -lm -lreadline -lsndfile -lasound
#
# object files
OBJS = main.o reformat.o session.o showhelp.o support.o players.o
docfiles = $$(find doc/ -maxdepth 1 -type f)
#
# installation directory
prefix = /usr/local
execprefix = $(prefix)
# Binary and documentation directories
bindir = $(execprefix)/bin
datarootdir = $(prefix)/share
docdir = $(datarootdir)/doc/edway
realbindir = $(DESTDIR)$(bindir)
realdocdir = $(DESTDIR)$(docdir)
#
# Defines:
defines = '-Dprogdir="$(docdir)"'
default: all
#
all: edway
%.o : %.c edway.h
	@ $(CC) $(CFLAGS) $(defines) -c $<
#
edway: $(OBJS)
	@ $(CC) $(CFLAGS) $(defines) -o edway $(OBJS) $(LIBS)
#
install:  install_bin install_doc
#
install_bin: edway
	@ $(INSTALL) -m755 -D edway $(realbindir)/edway
	@ ( cd $(realbindir) ; ln -sf edway ew )
#
install_doc:
	@ $(INSTALL) -m755 -d $(realdocdir) $(realdocdir)/extras $(realdocdir)/HELP
	@ $(INSTALL) -m644 $(docfiles) $(realdocdir)
	@ $(INSTALL) -m644 extras/* $(realdocdir)/extras
	@ $(INSTALL) -m644 doc/HELP/* $(realdocdir)/HELP
clean:
	@ rm -f edway $(OBJS) *~
#
tarball: clean
	@ cd .. ; tar czf edway-$(VER).$(REV).tar.gz edway-$(VER)
#
uninstall:
	@ ( rm -rf $(docdir) ; rm -f $(bindir)/edway ; \
	rm -f $(bindir)/ew ; )
#
# end of edway Makefile
