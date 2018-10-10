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


#include "ltorrent-client.h"

namespace lt = libtorrent;

char const* state(lt::torrent_status::state_t s)
{
	switch(s) {
		case lt::torrent_status::checking_files: return "checking";
		case lt::torrent_status::downloading_metadata: return "dl metadata";
		case lt::torrent_status::downloading: return "downloading";
		case lt::torrent_status::finished: return "finished";
		case lt::torrent_status::seeding: return "seeding";
		case lt::torrent_status::allocating: return "allocating";
		case lt::torrent_status::checking_resume_data: return "checking resume";
		default: return "<>";
	}
}

std::vector<std::string> split(const std::string& s, char delimiter)
{
   std::vector<std::string> tokens;
   std::string token;
   std::istringstream tokenStream(s);
   while (std::getline(tokenStream, token, delimiter))
   {
      tokens.push_back(token);
   }
   return tokens;
}

LtorrentClient::LtorrentClient(OptionParser opts)
    : _opts(opts) {}

bool LtorrentClient::running = true;
lt::session LtorrentClient::_sess;

int LtorrentClient::CreatePidfile() {
  auto pid = getpid();
  std::ofstream pidfile;
  pidfile.open(_opts.pidfile);
  pidfile << pid;
  pidfile << "\n";
  pidfile.close();
  return EXIT_SUCCESS;
}

int LtorrentClient::RemovePidfile() {
  if (remove(_opts.pidfile.c_str()) != 0) {
    std::cerr << "Error deleting pidfile\n";
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}

void LtorrentClient::StopHandler(int signal) {
  std::cout << "Stopping\n";
  running = false;
}

int LtorrentClient::RegisterHandlers() {
  std::signal(SIGINT, StopHandler);
  std::signal(SIGTERM, StopHandler);
  return EXIT_SUCCESS;
}

int LtorrentClient::SetPeerID() {
  char hostname[21];
  char hostname_tmp[HOST_NAME_MAX];
  gethostname(hostname_tmp, HOST_NAME_MAX);
  auto vhostname = split(std::string(hostname_tmp), '.');
  if (vhostname[0].length() > 20) {
    // we can't use hostname for peer_id  if hostname length is > 20 chars
    return EXIT_SUCCESS;
  }
  snprintf(hostname, sizeof(hostname), "%20s", vhostname[0].c_str());
  lt::peer_id my_peer_id = lt::sha1_hash(hostname);
  _sess.set_peer_id(my_peer_id);
  return EXIT_SUCCESS;
}

int LtorrentClient::BindPorts() {
  lt::error_code ec;
  auto settings = lt::session_settings();
  // disable unneeded features
  settings.ssl_listen = false;
  _sess.set_settings(settings);
  _sess.stop_natpmp();
  _sess.stop_upnp();
  _sess.stop_lsd();

  _sess.listen_on(std::make_pair(6881, 6889), ec, _opts.bindip.c_str());
  if (ec) {
    std::cerr << "failed to open listen socket: "
              << ec.message() << "\n";
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}

int LtorrentClient::DownloadTorrent() {

  _sess.set_alert_mask(
      lt::alert::error_notification
		| lt::alert::storage_notification
		| lt::alert::status_notification
  );

  // create torrent object
  lt::add_torrent_params p;
  lt::error_code ec;

  p.save_path = "./";
  p.ti = new lt::torrent_info(_opts.torrentfile, ec);
  if (ec)
  {
    std::cerr << ec.message() << "\n";
    return EXIT_FAILURE;
  }
  _sess.async_add_torrent(std::move(p));

  lt::torrent_handle h;

  while(running) {
    std::deque<lt::alert*> alerts;
    _sess.pop_alerts(&alerts);

    for (auto const* a : alerts) {
			if (auto at = lt::alert_cast<lt::add_torrent_alert>(a)) {
				h = at->handle;
			}

			// if we receive the finished alert or an error, we're done
			if (lt::alert_cast<lt::torrent_finished_alert>(a)) {
				h.save_resume_data();
        std::cout << "Finished\n";
        if (_opts.userpid > 0) {
          std::cout << "Sending SIGUSR1 to PID " << _opts.userpid << "\n";
          kill(_opts.userpid, SIGUSR1);
        }
			}
			if (lt::alert_cast<lt::torrent_error_alert>(a)) {
				std::cout << a->message() << "\n";
				running = false;
			}

			if (auto st = lt::alert_cast<lt::state_update_alert>(a)) {
				if (st->status.empty()) continue;

				// we only have a single torrent, so we know which one
				// the status is for
				lt::torrent_status const& s = st->status[0];
				std::cout  << state(s.state) << " "
					<< (s.download_payload_rate / 1000) << " kB/s "
					<< (s.total_done / 1000) << " kB ("
					<< (s.progress_ppm / 10000) << "%) downloaded\n";
				std::cout.flush();
			}
    }

    _sess.post_torrent_updates();
    h.save_resume_data();
    h.force_reannounce();
    std::this_thread::sleep_for(std::chrono::milliseconds(_opts.delay*1000));

  }
}

