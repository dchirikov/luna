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

bool Torrents::init() {
  log_trace(__PRETTY_FUNCTION__);
  libtorrent::error_code ec;
  session_.listen_on(
    std::make_pair(opts_.listenPortMin, opts_.listenPortMax),
    ec,
    opts_.listenIP.c_str()
  );
  if (ec) {
    log_error("Failed to open listen socket: " << ec.message());
    return false;
  }
  session_.set_peer_id(
    libtorrent::sha1_hash(opts_.agentName)
  );
  auto settings = libtorrent::session_settings(opts_.agentName);
  settings.announce_ip = opts_.listenIP;
  settings.ssl_listen = opts_.sslPort;
  session_.set_settings(settings);

  if (!opts_.natpmp)
    session_.stop_natpmp();
  if (!opts_.upnp)
    session_.stop_upnp();
  if (!opts_.lsd)
    session_.stop_lsd();

  return true;
}

bool Torrents::update() {
  log_trace(__PRETTY_FUNCTION__);
  updateLocalFiles_();
  updateLunaFiles_();
  seedOSImages_();
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
  // if we are unable to get torrent_info from *.torrent file,
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
  // now we need to add all local files to torrents_
  // with timestamps.
  torrentsLock_.lock();
  log_debug("Populate torrents_");
  for (auto it=localFiles.begin(); it != localFiles.end(); it++ ) {
    auto filename = (*it).filename;
    auto torrent_info = (*it).torrent_info;
    // if file is in torrents_, go to next
    if (torrents_.count(torrent_info.info_hash())) {
      log_debug("'" << filename << "' is in torrents_ already");
      continue;
    }

    // add new record
    log_debug("'" << filename << "' is not in torrents_");
    auto now = std::chrono::system_clock::now();
    torrents_.insert(
      std::pair<libtorrent::sha1_hash, lunaTorrent_t>(
        torrent_info.info_hash(),
        {filename, now, false, NOT_SEEDING, {}}
      )
    );

  }
  torrentsLock_.unlock();
  traceTorrents_();
}

void Torrents::updateLunaFiles_() {
  log_trace(__PRETTY_FUNCTION__);
  helpers::Runner r(opts_.getImagesCmd, "");
  r.exec();

  if (r.rc) {
    // something went wrong
    log_error("Unable to check osimages");
    if (r.err != "") {
      log_error("Get osimages STDERR: " << r.err);
    }
    return;
  }

  if (r.out == "") {
    // list of osimages is empty. It might be a valid case, but better be safe.
    log_debug("List of osimages is empty");
    return;
  }

  // here we are able to reach Luna and get list of osimages
  lastCheckedLuna_ = std::chrono::system_clock::now();
  log_debug("Get osimages STDOUT: " << r.out);
  auto lines = helpers::splitString(r.out);

  // convert list to map for quicker checks
  std::map<std::string, bool> lunaConfiguredTorrents;
  for (auto it = lines.begin(); it != lines.end(); it++) {
    auto filename = *it + TORRENT_FILE_EXTENSION;
    lunaConfiguredTorrents.insert(
        std::pair<std::string, bool>(filename, false));
  }

  // update torrents_
  torrentsLock_.lock();
  for (auto it = torrents_.begin(); it != torrents_.end(); it++ ) {
    auto fileName = (*it).second.torrentFile;
    if (!lunaConfiguredTorrents.count(fileName)) {
      log_debug("'" << fileName << "' is not in Luna");
      (*it).second.isInLuna = false;
      continue;
    }
    log_debug("'" << fileName << "' found in Luna");
    lunaConfiguredTorrents.at(fileName) = true;
    (*it).second.isInLuna = true;
    (*it).second.timeStamp = std::chrono::system_clock::now();
  }
  torrentsLock_.unlock();
  traceTorrents_();

  // report if we have some uuids without files on disks
  for (
      auto it =lunaConfiguredTorrents.begin();
      it !=lunaConfiguredTorrents.end();
      it++) {
    if (!(*it).second) {
      log_error("Torrent '" << (*it).first
          << "' presents in Luna but does not exist on disk.");
    }
  }
}

std::ostream& operator <<(std::ostream& os, const timeStamp_t& l) {
  auto t = std::chrono::system_clock::to_time_t(l);
  char buf[80];
  auto ts = *localtime(&t);
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &ts);
  os << buf;
  return os;
}

std::ostream& operator <<(
    std::ostream& os, const libtorrent::torrent_info& l) {
  os << l.name();
  return os;
}

std::ostream& operator <<(
    std::ostream& os, const libtorrent::torrent_handle& l) {

  std::vector<std::string> torrent_handlerConv{
    "queued_for_checking", "checking_files", "downloading_metadata",
    "downloading", "finished", "seeding", "allocating",
    "checking_resume_data"
  };

  os << torrent_handlerConv[l.status().state];
  return os;
}

/*
std::ostream& operator <<(
    std::ostream& os, const libtorrent::state_t& l) {
  return os;
} */

std::ostream& operator <<(
      std::ostream& os, const seedStatus_t& l) {

  std::vector<std::string> seedStatus_tConv{
    "NOT_SEEDING", "ADDED_FOR_SEEDING", "SEEDING", "MARKED_FOR_DELETION"
  };

  os << seedStatus_tConv[l];
  return os;
}

std::ostream& operator <<(std::ostream& os, const lunaTorrent_t& l) {
  os << "("
     << "torrentFile: '" << l.torrentFile << "', "
     << "timeStamp: '" << l.timeStamp << "', "
     << "isInLuna: " << l.isInLuna << ", "
     << "isSeeding: " << l.isSeeding << ", "
     << "torrentHandler: " << l.torrentHandler
     << ")";
  return os;
}

std::ostream& operator <<(std::ostream& os, const torrentsList_t& l) {
  os << "[ ";
  for (auto it = l.begin(); it != l.end(); it++) {
    os << (*it).first
       << ": " << (*it).second << ", ";
  }
  os << " ]";
  return os;
}

void Torrents::seedOSImages_() {
  log_trace(__PRETTY_FUNCTION__);
  torrentsLock_.lock();
  for (auto it = torrents_.begin(); it != torrents_.end(); it++) {

    // already seeding. nothing to do
    if ((*it).second.isSeeding != NOT_SEEDING) {
      log_debug("'" << (*it).second.torrentFile
          << "' is being seeded already.");
      continue;
    }

    // someone put torrent which is not related to luna
    if (!(*it).second.isInLuna) {
      log_debug("'" << (*it).second.torrentFile
          << "' is not in Luna. Skipping.");
      continue;
    }

    // finally seed osimage
    libtorrent::add_torrent_params p;
    libtorrent::error_code ec;
    p.ti = new libtorrent::torrent_info((*it).second.torrentFile, ec);
    if (ec)
    {
      log_error("Error on reading torrent file '"
          << (*it).second.torrentFile << "': " << ec.message());
      continue;
    }
    log_info("'" << (*it).second.torrentFile
        << "' added to ltorrent for seeding.");
    session_.async_add_torrent(std::move(p));
    (*it).second.isSeeding = ADDED_FOR_SEEDING;
  }
  torrentsLock_.unlock();
}

void Torrents::readAlerts() {
  std::deque<libtorrent::alert*> alerts;
  session_.pop_alerts(&alerts);
  for (auto const* a : alerts) {

    // catch adding alert
    if (auto at = libtorrent::alert_cast<libtorrent::add_torrent_alert>(a)) {
      auto h = at->handle;
      auto ti = *(h.torrent_file());
      log_info("'" << ti.name() << "' started seeding.");
      torrentsLock_.lock();
      auto elem = torrents_.find(h.info_hash());
      if (elem == torrents_.end()) {
        log_error("Some unknown file was added. This should not happen.");
        torrentsLock_.unlock();
        continue;
      }
      (*elem).second.isSeeding = SEEDING;
      (*elem).second.torrentHandler = h;
      torrentsLock_.unlock();
      traceTorrents_();
    }

    if (auto at = libtorrent::alert_cast<libtorrent::torrent_deleted_alert>(a)) {
      auto ih = at->info_hash;
      {
        auto elem = torrents_.find(ih);
        torrentsLock_.lock();
        if (elem == torrents_.end()) {
          log_error("torrent_deleted_alert received for unknown info_hash: '"
              << ih << "'");
          torrentsLock_.unlock();
          continue;
        }
        auto torrentFile = (*elem).second.torrentFile;
        if (std::remove(torrentFile.c_str()) != 0 ) {
          log_error("Unable to delete " << torrentFile);
        }
      }
      torrents_.erase(ih);
      torrentsLock_.unlock();
      traceTorrents_();
    }
  }
}

void Torrents::deleteOldTorrents() {
  log_trace(__PRETTY_FUNCTION__);
  torrentsLock_.lock();
  for (auto it = torrents_.begin(); it != torrents_.end(); it++) {
    if ((*it).second.isInLuna) {
      log_trace("'" << (*it).second.torrentFile << "' is in Luna.");
      // check if libtorrent failed to add our torrent in reasonable time
      if (
          ((*it).second.isSeeding != SEEDING)
          && (helpers::timeout(
                (*it).second.timeStamp,
                opts_.libtorrentAddTimeout))
      ) {
        log_error("'" << (*it).second.torrentFile
            << "' should be seeding, but it's not.");
      }
      continue;
    }

    // Torrent will be seeded for a while to let nodes which are stuck
    // on boot to get the images, despite tarball of osimage is replaced
    if (!helpers::timeout(
          (*it).second.timeStamp,
          opts_.holdingDeletedTorrentsSec
        )) {
      log_trace("'" << (*it).second.torrentFile
          << "' is deleted from Luna, but it did not hit timeout.");
      continue;
    }

    if ((!(*it).second.torrentHandler.is_valid())
        && ((*it).second.isSeeding != MARKED_FOR_DELETION)) {
      log_warning("Something is not right. '" << (*it).second.torrentFile
          << "' not in Luna and libtorrent handler is unknown.");
    }

    // Mark torrent ready for deletion
    (*it).second.isSeeding = MARKED_FOR_DELETION;

    // stop seeding and remove tarball
    log_info("Removing torrent from seeding '"
        << (*it).second.torrentFile << "'");
    session_.remove_torrent(
      (*it).second.torrentHandler,
      libtorrent::session::delete_files);

  }
  torrentsLock_.unlock();
  traceTorrents_();
}

void Torrents::traceTorrents_() {
  torrentsLock_.lock();
  log_trace("Torrents:");
  for (auto it = torrents_.begin(); it != torrents_.end(); it++) {
    log_trace((*it).first << ": " << (*it).second);
  }
  torrentsLock_.unlock();
}

