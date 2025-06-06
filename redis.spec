# TODO
# - Check for status of man pages http://code.google.com/p/redis/issues/detail?id=202
#
# Conditional build:
%bcond_without	tests		# build without tests
%bcond_without	perftools	# google perftools
%bcond_without	systemd		# systemd support
%bcond_without	system_jemalloc	# use embedded jemalloc

%ifnarch %{ix86} %{x8664} ppc
# available only on selected architectures
%undefine	with_perftools
%endif

Summary:	A persistent key-value database
Name:		redis
Version:	8.0.1
Release:	1
License:	AGPLv3
Group:		Applications/Databases
Source0:	http://download.redis.io/releases/%{name}-%{version}.tar.gz
# Source0-md5:	065162870a195ac75c878c2e2e66f035
Source1:	%{name}.logrotate
Source2:	%{name}.init
Source3:	%{name}.tmpfiles
Source4:	%{name}.service
Source5:	%{name}.sysconfig
Patch0:		%{name}.conf.patch
Patch1:		%{name}-tcl.patch
Patch2:		0001-1st-man-pageis-for-redis-cli-redis-benchmark-redis-c.patch
Patch3:		arm-arch-check.patch
Patch4:		system-jemalloc.patch
URL:		http://www.redis.io/
%{?with_perftools:BuildRequires:    gperftools-devel}
%ifnarch %{arm}
BuildRequires:	jemalloc-devel
%endif
%ifarch %{arm}
BuildRequires:	libatomic-devel
%endif
BuildRequires:	openssl-devel
BuildRequires:	pkgconfig
BuildRequires:	rpm >= 4.4.9-56
BuildRequires:	rpmbuild(macros) >= 2.011
BuildRequires:	sed >= 4.0
%{?with_systemd:BuildRequires:	systemd-devel}
%{?with_tests:BuildRequires:	tcl >= 8.5}
Obsoletes:	redis-doc
Conflicts:	logrotate < 3.8.0
ExcludeArch:	sparc sparc64 alpha
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
Redis is an advanced key-value store. It is similar to memcached but
the data set is not volatile, and values can be strings, exactly like
in memcached, but also lists, sets, and ordered sets. All this data
types can be manipulated with atomic operations to push/pop elements,
add/remove elements, perform server side union, intersection,
difference between sets, and so forth. Redis supports different kind
of sorting abilities.

%package server
Summary:	Persistent key-value database with network interface
Group:		Applications/Databases
Requires(post,preun):	/sbin/chkconfig
Requires(postun):	/usr/sbin/groupdel
Requires(postun):	/usr/sbin/userdel
Requires(pre):	/bin/id
Requires(pre):	/usr/bin/getgid
Requires(pre):	/usr/sbin/groupadd
Requires(pre):	/usr/sbin/useradd
Requires:	rc-scripts
Provides:	group(redis)
Provides:	user(redis)

%description server
Redis is a key-value database in a similar vein to memcache but the
dataset is non-volatile. Redis additionally provides native support
for atomically manipulating and querying data structures such as lists
and sets.

The dataset is stored entirely in memory and periodically flushed to
disk.

%prep
%setup -q
%patch -P0 -p1
%patch -P1 -p1
%patch -P2 -p1
%patch -P3 -p1
%patch -P4 -p1

# Remove integration tests
%{__sed} -i -e '/    integration\/replication/d' tests/test_helper.tcl
%{__sed} -i -e '/    unit\/memefficiency/d' tests/test_helper.tcl

# randomize port number so concurrent builds doesn't break
port=$((21110 + ${RANDOM:-$$} % 1000))
sed -i -e "s/set ::port 21111/set ::port $port/" tests/test_helper.tcl

%{__rm} -r deps/jemalloc

%build
%define _make_opts \\\
	CC="%{__cc}" \\\
	CFLAGS="%{rpmcflags}" \\\
	LDFLAGS="%{rpmldflags}" \\\
	OPTIMIZATION="" \\\
	DEBUG="" \\\
	BUILD_TLS=yes \\\
	USE_SYSTEMD=%{?with_systemd:yes}%{!?with_systemd:no} \\\
	V=1 \\\
	uname_M=%{_target_cpu}

%{__make} -C src all

%if %{with tests}
%{__make} test
%endif

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT{%{_sysconfdir},/etc/sysconfig,%{_sbindir}} \
	$RPM_BUILD_ROOT/etc/{logrotate.d,rc.d/init.d} \
	$RPM_BUILD_ROOT%{_localstatedir}/{{lib,log,run}/%{name},log/archive/%{name}} \
	$RPM_BUILD_ROOT%{systemdtmpfilesdir} $RPM_BUILD_ROOT%{systemdunitdir} \
	$RPM_BUILD_ROOT%{_mandir}/man{1,5}

%{__make} install \
	INSTALL="install -p" \
	PREFIX=$RPM_BUILD_ROOT%{_prefix}

# Fix non-standard-executable-perm error
chmod a+x $RPM_BUILD_ROOT%{_bindir}/%{name}-*

# Ensure redis-server location doesn't change
mv $RPM_BUILD_ROOT{%{_bindir},%{_sbindir}}/%{name}-server
mv $RPM_BUILD_ROOT{%{_bindir},%{_sbindir}}/%{name}-sentinel

# Install misc other
install -p %{SOURCE2} $RPM_BUILD_ROOT/etc/rc.d/init.d/%{name}
cp -p %{SOURCE1} $RPM_BUILD_ROOT/etc/logrotate.d/%{name}
cp -p %{name}.conf $RPM_BUILD_ROOT%{_sysconfdir}
cp -p %{SOURCE3} $RPM_BUILD_ROOT%{systemdtmpfilesdir}/%{name}.conf
%{?with_systemd:%{__sed} -e 's;@sbindir@;%{_sbindir};' -e 's;@localstatedir@;%{_localstatedir};' %{SOURCE4} > $RPM_BUILD_ROOT%{systemdunitdir}/%{name}.service}
%{__sed} -e 's;@sysconfdir@;%{_sysconfdir};' %{SOURCE5} > $RPM_BUILD_ROOT/etc/sysconfig/%{name}

# man-pages
for man in man/man1/*; do
	install $man $RPM_BUILD_ROOT%{_mandir}/man1
done
for man in man/man5/*; do
	install $man $RPM_BUILD_ROOT%{_mandir}/man5
done

# sentinel can be symlinked
echo ".so man1/redis-server.1" > $RPM_BUILD_ROOT%{_mandir}/man1/redis-sentinel.1
echo ".so man5/redis.conf.5" > $RPM_BUILD_ROOT%{_mandir}/man5/redis-sentinel.conf.5

%clean
rm -rf $RPM_BUILD_ROOT

%pre server
%groupadd -g 256 redis
%useradd -u 256 -g redis -d %{_sharedstatedir}/redis -s /sbin/nologin -c 'Redis Server' redis

%post server
/sbin/chkconfig --add redis
%service redis restart
%{?with_systemd:%systemd_post %{name}.service}

%preun server
if [ "$1" = 0 ]; then
	%service redis stop
	/sbin/chkconfig --del redis
fi

%postun server
if [ "$1" = "0" ]; then
	%userremove redis
	%groupremove redis
fi
%{?with_systemd:%systemd_reload}

%triggerpostun server -- redis-server < 6.2.5-2
%{?with_systemd?%systemd_trigger %{name}.service}

%files
%defattr(644,root,root,755)
%doc 00-RELEASENOTES BUGS CONTRIBUTING.md INSTALL LICENSE.txt MANIFESTO README.md
%attr(755,root,root) %{_bindir}/redis-benchmark
%attr(755,root,root) %{_bindir}/redis-cli
%{_mandir}/man1/redis-benchmark.1*
%{_mandir}/man1/redis-cli.1*

%files server
%defattr(644,root,root,755)
%attr(640,root,root) %config(noreplace) %verify(not md5 mtime size) /etc/sysconfig/%{name}
%config(noreplace) %verify(not md5 mtime size) %{_sysconfdir}/%{name}.conf
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%attr(755,root,root) %{_sbindir}/redis-sentinel
%attr(755,root,root) %{_sbindir}/redis-server
%attr(755,root,root) %{_bindir}/redis-check-aof
%attr(755,root,root) %{_bindir}/redis-check-rdb
%config(noreplace) /etc/logrotate.d/%{name}
%dir %attr(750,redis,redis) %{_localstatedir}/lib/%{name}
%dir %attr(750,redis,redis) %{_localstatedir}/log/%{name}
%dir %attr(750,redis,redis) %{_localstatedir}/log/archive/%{name}
%dir %attr(750,redis,redis) %{_localstatedir}/run/%{name}
%{systemdtmpfilesdir}/%{name}.conf
%{?with_systemd:%{systemdunitdir}/%{name}.service}
%{_mandir}/man1/redis-sentinel.1*
%{_mandir}/man1/redis-server.1*
%{_mandir}/man1/redis-check-aof.1*
%{_mandir}/man1/redis-check-rdb.1*
%{_mandir}/man5/redis.conf.5*
%{_mandir}/man5/redis-sentinel.conf.5*
