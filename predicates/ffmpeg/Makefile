# Builds lib/ffmpeg_g-<commit> (debug + AddressSanitizer) for each commit.

COMMITS := 466799d4f5 8d24a28d06
REPO    := https://github.com/FFmpeg/FFmpeg.git
SRCDIR  := build
NPROC   := $(shell nproc)

TARGETS := $(patsubst %,lib/ffmpeg_g-%,$(COMMITS))

.NOTPARALLEL:
.PHONY: all clean distclean

all: $(TARGETS)

$(SRCDIR):
	git clone $(REPO) $(SRCDIR)

lib/ffmpeg_g-%: $(SRCDIR)
	cd $(SRCDIR) && git checkout $* && git clean -fdx

	cd $(SRCDIR) && ./configure \
		--cc=clang \
		--cxx=clang++ \
		--ld=clang \
		--enable-debug \
		--disable-x86asm

	sed -i '/^CFLAGS=/s/$$/ -fsanitize=address -fno-omit-frame-pointer/' $(SRCDIR)/ffbuild/config.mak
	sed -i '/^LDFLAGS=/s/$$/ -fsanitize=address/' $(SRCDIR)/ffbuild/config.mak

	$(MAKE) -C $(SRCDIR) -j$(NPROC)

	mkdir -p lib
	cp $(SRCDIR)/ffmpeg_g $@

clean:
	rm -rf lib/

distclean:
	rm -rf lib/ $(SRCDIR)
