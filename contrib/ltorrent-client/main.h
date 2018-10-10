/*
* Written by Dmitry Chirikov <dmitry@chirikov.ru>
* This file is part of Luna, cluster provisioning tool
* https://github.com/dchirikov/luna
*
* This file is part of Luna.
*
* Luna is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.

* Luna is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Luna.  If not, see <http://www.gnu.org/licenses/>.
*/

#include <stdlib.h>
#include "optionparser.h"
#include "ltorrent-client.h"
#include <exception>

#define run(method)               \
try {                             \
  rc = method();                  \
}                                 \
catch (const std::exception& e) { \
  std::cerr << e.what();          \
  rc = EXIT_FAILURE;              \
}                                 \
if (rc) {                         \
  exit(rc);                       \
}                                 \

