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

#include "torrents.hpp"

Torrents::Torrents(const OptionParser &opts)
  : opts_(opts),
    torrentsMutex_(),
    torrentsLock_(torrentsMutex_, std::defer_lock),
    logger_(log4cplus::Logger::getInstance(DEFAULT_LOGGER_NAME))
{
  log_trace(__PRETTY_FUNCTION__);
};

bool Torrents::update() {
  log_trace(__PRETTY_FUNCTION__);
  updateLocalFiles_();
  updateLunaFiles_();
}

localFile_t Torrents::parseTorrentFile_(std::string f) {
  int suf_len = std::string(TORRENT_FILE_EXTENSION).size();
  // skip if len < ".torrent".size()
  if (f.size() < suf_len) {
    log_trace("Skipping '" << f << "'");
    throw(LtorrentsException(""));
  }
  // skip if not ends with ".torrent"
  if (f.compare(
        f.size()-suf_len,
        std::string::npos,
        TORRENT_FILE_EXTENSION
      ) != 0) {
    log_trace("Skipping '" << f << "'");
    throw(LtorrentsException(""));
  }
  log_info("Torrent file is found: " << f);
  // if we unable to get torrent_info from *.torrent file,
  // it is nothing we can do.
  try {
    auto file_info = libtorrent::torrent_info(f, 0);
    log_trace("'" << f << "': "
        << "info hash for file: '" << file_info.info_hash() << "'; "
        << "name is '" << file_info.name() << "'");
    for (auto i=0; i < file_info.files().num_files(); i++ ) {
      log_trace("'" << f << "'; i=" << i << "; file: '"
        << file_info.files().file_name(i) << "'"
      );
    }
    localFile_t ret {f, file_info};
    return ret;
  } catch(const libtorrent::libtorrent_exception& e) {
    log_warning("Error for file: '" << f << "': " << e.what());
    throw(LtorrentsException(""));
  }
}

void Torrents::updateLocalFiles_() {
  log_trace(__PRETTY_FUNCTION__);
  auto files = helpers::readDirectory(".");
  log_debug("Files in current working dir: " << files);
  std::vector<localFile_t> localFiles;
  for (auto it = files.begin(); it != files.end(); it++) {
    try {
    auto localFile = parseTorrentFile_(*it);
    localFiles.push_back(localFile);
    } catch(const LtorrentsException& e) {
      continue;
    }
  }
  // now we need to add all local files to torrentsLock_
  // with timestamps. later those will be updated if
  torrentsLock_.lock();
  log_trace("Populate torrentsLock_");
  for (auto it=localFiles.begin(); it != localFiles.end(); it++ ) {
    auto filename = (*it).filename;
    auto torrent_info = (*it).torrent_info;
    // if file is in torrentsLock_, go to next
    if (torrents_.count(filename)) {
      continue;
    }
    log_trace("'" << filename << "' is not in torrentsLock_");
    auto now = std::chrono::system_clock::now();
    torrents_.insert(
      std::pair<std::string, lunaTorrent_t>(
        filename, {torrent_info, now, false}
      )
    );
  }
  torrentsLock_.unlock();
}

void Torrents::updateLunaFiles_() {
  log_trace(__PRETTY_FUNCTION__);
}
