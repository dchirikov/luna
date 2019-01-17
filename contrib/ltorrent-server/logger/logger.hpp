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

#pragma once

#include <log4cplus/logger.h>
#include <log4cplus/configurator.h>
#include <log4cplus/loggingmacros.h>
#include <log4cplus/consoleappender.h>
#include <log4cplus/fileappender.h>
#include <log4cplus/loglevel.h>
#include <memory>

#include "../config.hpp"
#include "../optionparser/optionparser.hpp"

#define log_error(msg) LOG4CPLUS_ERROR(logger_, msg)
#define log_warning(msg) LOG4CPLUS_WARN(logger_, msg)
#define log_info(msg) LOG4CPLUS_INFO(logger_, msg)
#define log_debug(msg) LOG4CPLUS_DEBUG(logger_, msg)
#define log_trace(msg) LOG4CPLUS_TRACE(logger_, msg)

void init_logger(const OptionParser &opts);
