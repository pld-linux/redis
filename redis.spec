# TODO
# - Check for status of man pages http://code.google.com/p/redis/issues/detail?id=202
#
# Conditional build:
%if "%{pld_release}" == "ac"
%bcond_with		tests		# build without tests
%else
%bcond_without	tests		# build without tests
%endif

Summary:	A persistent key-value database
Name:		redis
Version:	2.0.2
Release:	4
License:	BSD
Group:		Applications/Databases
URL:		http://code.google.com/p/redis/
Source0:	http://redis.googlecode.com/files/%{name}-%{version}.tar.gz
# Source0-md5:	1658ab25161efcc0d0e98b4d1e38a985
Source1:	%{name}.logrotate
Source2:	%{name}.init
Patch0:		%{name}.conf.patch
BuildRequires:	rpm >= 4.4.9-56
BuildRequires:	rpmbuild(macros) >= 1.202
BuildRequires:	sed >= 4.0
%{?with_tests:BuildRequires:	tcl >= 8.5}
ExcludeArch:	sparc sparc64
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

%package doc
Summary:	documentation for redis
Group:		Documentation

%description doc
HTML Documentation for Redis.

%prep
%setup -q
%patch0 -p1
# Remove integration tests
%{__sed} -i -e '/    execute_tests "integration\/replication"/d' tests/test_helper.tcl
%{__sed} -i -e '/    execute_tests "integration\/aof"/d' tests/test_helper.tcl

%build
%{__make} all \
	DEBUG="" \
	CC="%{__cc}" \
	CFLAGS="%{rpmcflags} -std=c99"

%if %{with tests}
tclsh tests/test_helper.tcl
%endif

%install
rm -rf $RPM_BUILD_ROOT
# Install binaries
install -p -D %{name}-benchmark $RPM_BUILD_ROOT%{_bindir}/%{name}-benchmark
install -p -D %{name}-cli $RPM_BUILD_ROOT%{_bindir}/%{name}-cli
install -p -D %{name}-check-aof $RPM_BUILD_ROOT%{_bindir}/%{name}-check-aof
install -p -D %{name}-check-dump $RPM_BUILD_ROOT%{_bindir}/%{name}-check-dump
install -p -D %{name}-server $RPM_BUILD_ROOT%{_sbindir}/%{name}-server
# Install misc other
install -p -D %{SOURCE1} $RPM_BUILD_ROOT/etc/logrotate.d/%{name}
install -p -D %{SOURCE2} $RPM_BUILD_ROOT/etc/rc.d/init.d/%{name}
install -p -D %{name}.conf $RPM_BUILD_ROOT%{_sysconfdir}/%{name}.conf
install -d $RPM_BUILD_ROOT%{_localstatedir}/lib/%{name}
install -d $RPM_BUILD_ROOT%{_localstatedir}/log/%{name}
install -d $RPM_BUILD_ROOT%{_localstatedir}/run/%{name}

%clean
rm -fr $RPM_BUILD_ROOT

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
%doc COPYING 00-RELEASENOTES BUGS Changelog README TODO
%attr(755,root,root) %{_bindir}/redis-benchmark
%attr(755,root,root) %{_bindir}/redis-check-aof
%attr(755,root,root) %{_bindir}/redis-check-dump
%attr(755,root,root) %{_bindir}/redis-cli

%files server
%defattr(644,root,root,755)
%config(noreplace) %{_sysconfdir}/%{name}.conf
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%attr(755,root,root) %{_sbindir}/redis-server
%config(noreplace) /etc/logrotate.d/%{name}
%dir %attr(755,redis,root) %{_localstatedir}/lib/%{name}
%dir %attr(755,redis,root) %{_localstatedir}/log/%{name}
%dir %attr(755,redis,root) %{_localstatedir}/run/%{name}

%files doc
%defattr(644,root,root,755)
%doc doc/*
