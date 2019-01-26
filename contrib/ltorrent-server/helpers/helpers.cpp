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

#include "helpers.hpp"


int helpers::create_dir(const std::string& path) {
  struct stat info;
  if (stat(path.c_str(), &info) == 0 ) {
    if ((info.st_mode & S_IFMT) == S_IFDIR) {
      return(EXIT_SUCCESS);
    } else {
      // logger is unavailable here yet, so use stderr
      std::cerr << "'" << path << "' exists and not directory\n";
      return(EXIT_FAILURE);
    }
  }
  if (mkdir(path.c_str(), 0750)) {
    std::perror(path.c_str());
    std::cerr << "Unable to create dir '" << path << "'\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::chowner(const std::string& path, uid_t pw_uid, gid_t pw_gid) {
  if (chown(path.c_str(), pw_uid, pw_gid)) {
    std::perror(path.c_str());
    std::cerr << "Unable to chown "
      << pw_uid << ":" << pw_gid << " " << path << "\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::create_dir_and_chown(const std::string& path, uid_t pw_uid, gid_t pw_gid) {
  if (create_dir(path)) {
    return(EXIT_FAILURE);
  }
  if (chowner(path, pw_uid, pw_gid)) {
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::createDirs(const OptionParser &opts) {
  if (create_dir_and_chown(opts.logDir, opts.pw_uid, opts.pw_gid)) {
    return(EXIT_FAILURE);
  }
  if (create_dir_and_chown(opts.pidDir, opts.pw_uid, opts.pw_gid)) {
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

bool helpers::pidFileExists(const OptionParser &opts) {
  // check if pid file exists
  struct stat info;
  if (stat(opts.pidFile.c_str(), &info) != 0 ) {
    return(false);
  }
  // check if piddile is a file, actually
  if (!((info.st_mode & S_IFMT) == S_IFREG)) {
    std::cerr << "'" << opts.pidFile << "' is not a regular file\n";
    return(false);
  }
  return(true);
}

int helpers::killProcess(const OptionParser &opts) {
  if (!pidFileExists(opts)) {
    std::perror("Error accessing PID file");
    std::cerr << "Unable to find '" << opts.pidFile << "'. "
      << "Is daemon running?\n";
    return(EXIT_FAILURE);
  }
  // read pid from pidfile
  std::ifstream pidfile(opts.pidFile);
  pid_t pid;
  pidfile >> pid;
  std::cout << "Trying to kill process with PID " << pid << "\n";
  // check if process exists
  if (kill(pid, 0)) {
    std::cerr << "Process with PID '" << pid << "' is not running\n";
    return(EXIT_FAILURE);
  }
  // get process group for PID
  pid_t pgid;
  pgid = getpgid(pid);

  int seconds = 0;
  while (seconds < opts.killtimeout) {
    sleep(1);
    if (killpg(pgid, SIGTERM)) {
      return(EXIT_SUCCESS);
    }
    seconds++;
  }
  std::cerr << "Timeout killing process. Sending SIGKILL.\n";
  killpg(pgid, SIGKILL);
  // do cleanup for killed process
  if (std::remove(opts.pidFile.c_str()) != 0 ) {
    std::cerr << "Unable to delete '" << opts.pidFile << "'\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::changeUser(const OptionParser &opts) {
  if (setuid(opts.pw_uid)) {
    std::perror("Unable to change user");
    std::cerr << "Unable to change EUID to " << opts.pw_uid
      << " to run as " << opts.user <<  "\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

std::vector<std::string> helpers::readDirectory(const std::string& name) {
  std::vector<std::string> res;
  DIR* dirp = opendir(name.c_str());
  struct dirent * dp;
  while ((dp = readdir(dirp)) != NULL) {
    res.push_back(dp->d_name);
  }
  closedir(dirp);
  return res;
}

std::ostream& operator <<(
    std::ostream& os, const std::vector<std::string>& v) {
  for (auto it = v.begin(); it != v.end(); it++) {
    os << *it << "; ";
  }
  return os;
}

helpers::Runner::Runner(const std::string& cmd, const std::string& input, int timeout)
  : input_(input), timeout_(timeout), out_(), err_()
{
    typedef boost::tokenizer< boost::escaped_list_separator<char> > Tokenizer;
    boost::escaped_list_separator<char> Separator( '\\', ' ', '\"' );
    Tokenizer tok(cmd, Separator );

    for( auto it = tok.begin(); it != tok.end(); ++it )
      arguments_.push_back(*it);

}

helpers::Runner::Runner(const std::vector<std::string>& cmd, const std::string& input, int timeout)
  : input_(input), timeout_(timeout), out_(), err_()
{
    for (auto it = cmd.begin(); it != cmd.end(); ++it )
      arguments_.push_back(*it);

}

bool helpers::Runner::readPipe_(int p, std::ostringstream& out) {
    int nread = 0;
    char buf[msgSize_];
    // read call if return -1 then pipe is
    // empty because of fcntl
    nread = read(p, buf, msgSize_);
    switch (nread) {
    case -1:

        // case -1 means pipe is empty and errono
        // set EAGAIN
        if (errno == EAGAIN) {
            return false;
        }

        else {
            perror("read");
            return true;
        }

    // case 0 means all bytes are read and EOF(end of conv.)
    case 0:
        return true;

    default:

        // text read
        // by default return no. of bytes
        // which read call read at that time
        out << std::string(buf).substr(0, nread);
        return false;
    }
}

void helpers::Runner::parentRead_(int po, int pe) {

    bool endo = false;
    bool ende = false;
    bool exited = false;
    int status = 0;
    std::time_t started = std::time(nullptr);
    while (1) {
      if (endo & ende & exited)
        break;
      if (!endo)
        endo = readPipe_(po, out_);
      if (!ende)
        ende = readPipe_(pe, err_);
      if (!exited) {
        auto w = waitpid(childpid_,  &status, WNOHANG);
        if (w == childpid_) {
          exited = true;
        }
        if (w < 0) {
          err_ << "waitpid() returned -1";
          rc = EXIT_FAILURE;
          exited = true;
        }
      }

      if( WIFEXITED(status) ) {
        rc = WEXITSTATUS(status);
      }
      if (WIFSIGNALED(status)) {
        rc = WEXITSTATUS(status);
      }

      // check if we reached timeout
      std::time_t now = std::time(nullptr);
      if (now - started > timeout_) {
        kill(childpid_, SIGKILL);
        rc = EXIT_FAILURE;
        err = "Timeout.";
        return;
      }

      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    out = out_.str();
    err = err_.str();

}

void helpers::Runner::exec() {
  // stdin, stdout, stderr
  int proc_parent=0;
  int proc_child=1;
  int pipes[3][2];
  for (int i = STDIN_FILENO; i <= STDERR_FILENO; i++) {
    if (pipe(pipes[i]) < 0) {
      err = "Unable to create pipe.";
      rc = EXIT_FAILURE;
      return;
    }
    // enable non-blocking IO
    if (fcntl(*pipes[i], F_SETFL, O_NONBLOCK) < 0) {
      err = "Unable to set fcntl.";
      rc = EXIT_FAILURE;
      return;
    }
  }
  childpid_ = fork();
  if (!childpid_) {

    // child

    dup2(pipes[STDIN_FILENO][proc_parent], STDIN_FILENO);

    // close previously duplicated pipes
    for (int i = STDOUT_FILENO; i <= STDERR_FILENO; i++) {
      dup2(pipes[i][proc_child], i);
      for (int j = 0; j < 2; j++) {
        close(pipes[i][j]);
      }
    }

    // convert arguments from vector to array
    const char **argv = new const char* [arguments_.size()+1];
    for (int i = 0;  i < arguments_.size();  ++i) {
      argv[i] = arguments_[i].c_str();
    }

    argv[arguments_.size()] = NULL;

    execv(argv[0], (char **)argv);
  }

  // parent

  // close unneeded parent's pipes
  close(pipes[STDIN_FILENO][proc_parent]);
  for (int i = STDOUT_FILENO; i <= STDERR_FILENO; i++) {
    close(pipes[i][proc_child]);
  }

  // write to child's stdin
  write(
    pipes[STDIN_FILENO][proc_child],
    input_.c_str(),
    input_.size()
  );

  // read from pipes and check for timeout
  parentRead_(
    pipes[STDOUT_FILENO][proc_parent],
    pipes[STDERR_FILENO][proc_parent]
  );

  // close pipes

  close(pipes[STDIN_FILENO][proc_child]);
  close(pipes[STDERR_FILENO][proc_parent]);
  close(pipes[STDOUT_FILENO][proc_parent]);

  return;
}

std::vector<std::string> helpers::splitString(
    const std::string& s, const std::string& d) {

  std::vector<std::string> strings;

  std::string::size_type pos = 0;
  std::string::size_type prev = 0;
  while ((pos = s.find(d, prev)) != std::string::npos) {
    auto elem = s.substr(prev, pos - prev);
    if (elem != "") {
      strings.push_back(elem);
    }
    prev = pos + d.size();
  }

  auto rest = s.substr(prev);
  if ((rest != d) & (rest != "")) {
    strings.push_back(rest);
  }
  return strings;
}

bool helpers::timeout(
      const std::chrono::system_clock::time_point& timestamp,
      int sec) {

  auto now = std::chrono::system_clock::now();

  int diff = (
    std::chrono::duration_cast<std::chrono::seconds>(now - timestamp)
  ).count();

  return(diff > sec);
}
