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

#include "logger.hpp"

void init_logger(const OptionParser &opts) {
  log4cplus::initialize();
  log4cplus::tstring  pattern = opts.logPatternInfo;
  if (opts.logLevel < log4cplus::INFO_LOG_LEVEL) {
    pattern = opts.logPatternDebug;
  }
  log4cplus::Layout * layout = new log4cplus::PatternLayout(pattern);

  log4cplus::SharedAppenderPtr appender;

  if (opts.daemonize) {
    appender = new log4cplus::RollingFileAppender(
      LOG4CPLUS_TEXT(opts.logFile), opts.logSize, opts.logNum, opts.logFlush
    );
    appender->setName("file");
  } else {
    appender = new log4cplus::ConsoleAppender(opts.logToSTDERR, opts.logFlush);
    appender->setName("console");
  }

  appender->setLayout(std::auto_ptr<log4cplus::Layout>(layout));
  auto logger(log4cplus::Logger::getInstance(
      LOG4CPLUS_TEXT(DEFAULT_LOGGER_NAME)
  ));
  logger.addAppender(appender);
  logger.setLogLevel(opts.logLevel);


}
