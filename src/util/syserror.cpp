// Copyright (c) 2020-2022 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#if defined(HAVE_CONFIG_H)
#include <config/BGL-config.h>
#endif

#include <tinyformat.h>
#include <util/syserror.h>

#include <cstring>
#include <string>

std::string SysErrorString(int err)
{
    char buf[1024];
    /* Too bad there are three incompatible implementations of the
     * thread-safe strerror. */
    const char *s;
#ifdef WIN32
    s = buf;
    if (strerror_s(buf, sizeof(buf), err) != 0)
        buf[0] = 0;
#else
#ifdef STRERROR_R_CHAR_P /* GNU variant can return a pointer outside the passed buffer */
    s = strerror_r(err, buf, sizeof(buf));
#else /* POSIX variant always returns message in buffer */
    if (strerror_r(err, buf, sizeof(buf)) == 0) s = buf;
#endif
#endif
    return strprintf("%s (%d)", s, err);
}
