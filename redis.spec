# TODO
# - Check for status of man pages http://code.google.com/p/redis/issues/detail?id=202
# - use shared jemalloc?
#
# Conditional build:
%bcond_without	tests		# build without tests
%bcond_without	perftools	# google perftools

%ifnarch %{ix86} %{x8664} ppc
# available only on selected architectures
%undefine	with_perftools
%endif

Summary:	A persistent key-value database
Name:		redis
Version:	2.8.24
Release:	1
License:	BSD
Group:		Applications/Databases
Source0:	http://download.redis.io/releases/%{name}-%{version}.tar.gz
# Source0-md5:	7b6eb6e4ccc050c351df8ae83c55a035
Source1:	%{name}.logrotate
Source2:	%{name}.init
Source3:	%{name}.tmpfiles
Patch0:		%{name}.conf.patch
Patch1:		%{name}-tcl.patch
URL:		http://www.redis.io/
%{?with_perftools:BuildRequires:    gperftools-devel}
BuildRequires:	jemalloc-static
BuildRequires:	rpm >= 4.4.9-56
BuildRequires:	rpmbuild(macros) >= 1.202
BuildRequires:	sed >= 4.0
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
%patch0 -p1
%patch1 -p1

# Remove integration tests
%{__sed} -i -e '/    integration\/replication/d' tests/test_helper.tcl
%{__sed} -i -e '/    unit\/memefficiency/d' tests/test_helper.tcl

# randomize port number so concurrent builds doesn't break
port=$((21110 + ${RANDOM:-$$} % 1000))
sed -i -e "s/set ::port 21111/set ::port $port/" tests/test_helper.tcl

# use system jemalloc
mv deps/jemalloc{,-local}
install -d deps/jemalloc
ln -s %{_libdir} deps/jemalloc/lib
ln -s %{_includedir} deps/jemalloc/include

%build
%define specflags -std=c99 -pedantic
%define _make_opts CC="%{__cc}" CFLAGS="%{rpmcflags}" LDFLAGS="%{rpmldflags}" OPTIMIZATION="" DEBUG="" V=1

%{__make} -j1 -C src all

%if %{with tests}
%{__make} -j1 test
%endif

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT{%{_sysconfdir},%{_sbindir}} \
	$RPM_BUILD_ROOT/etc/{logrotate.d,rc.d/init.d} \
	$RPM_BUILD_ROOT%{_localstatedir}/{{lib,log,run}/%{name},log/archive/%{name}} \
	$RPM_BUILD_ROOT%{systemdtmpfilesdir}

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

%clean
rm -rf $RPM_BUILD_ROOT

%pre server
%groupadd -g 256 redis
%useradd -u 256 -g redis -d %{_sharedstatedir}/redis -s /sbin/nologin -c 'Redis Server' redis

%post server
/sbin/chkconfig --add redis
%service redis restart

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

%files
%defattr(644,root,root,755)
%doc COPYING 00-RELEASENOTES BUGS README
%attr(755,root,root) %{_bindir}/redis-benchmark
%attr(755,root,root) %{_bindir}/redis-check-aof
%attr(755,root,root) %{_bindir}/redis-check-dump
%attr(755,root,root) %{_bindir}/redis-cli

%files server
%defattr(644,root,root,755)
%config(noreplace) %{_sysconfdir}/%{name}.conf
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%attr(755,root,root) %{_sbindir}/redis-sentinel
%attr(755,root,root) %{_sbindir}/redis-server
%config(noreplace) /etc/logrotate.d/%{name}
%dir %attr(755,redis,root) %{_localstatedir}/lib/%{name}
%dir %attr(755,redis,root) %{_localstatedir}/log/%{name}
%dir %attr(755,redis,root) %{_localstatedir}/log/archive/%{name}
%dir %attr(755,redis,root) %{_localstatedir}/run/%{name}
%{systemdtmpfilesdir}/%{name}.conf
