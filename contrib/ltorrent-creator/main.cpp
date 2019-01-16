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

#include "main.hpp"

int main(int argc, char* argv[]) {
  auto opts = OptionParser(argc, argv);
  init_logger(opts);
  auto logger = log4cplus::Logger::getInstance(DEFAULT_LOGGER_NAME);

  log_debug("Options are parsed.");
  log_debug(opts);

  libtorrent::file_storage fs;
  libtorrent::add_files(fs, opts.tarball);
  libtorrent::create_torrent t(fs);
  t.add_tracker(opts.tracker);
  t.set_creator(opts.creator.c_str());
  t.set_comment(opts.tarball.c_str());
  libtorrent::set_piece_hashes(t, opts.tarballDir);
  {
    std::ofstream out(opts.torrent, std::ios_base::binary);
    libtorrent::bencode(std::ostream_iterator<char>(out), t.generate());
  }

  log_trace("Quit.");

  exit(EXIT_SUCCESS);
}
