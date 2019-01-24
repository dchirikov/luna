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

#include "tests.hpp"
#include <iostream>

int main(int argc, char* argv[]) {
  {
    helpers::Runner r("/usr/bin/bc -q", "2^32\nquit\n");
    r.exec();
    assert((r.rc == 0));
    assert((r.out == "4294967296\n"));
    assert((r.err == ""));
  }
  {
    std::vector<std::string> cmd{"/usr/bin/bc", "-q"};
    helpers::Runner r(cmd, "2^32\nquit\n");
    r.exec();
    assert((r.rc == 0));
    assert((r.out == "4294967296\n"));
    assert((r.err == ""));
  }
  {
    helpers::Runner r("/usr/bin/python -c \"print chr(10).join(['A', 'B', 'C'])\"", "");
    r.exec();
    assert((r.rc == 0));
    assert((r.out == "A\nB\nC\n"));
    assert((r.err == ""));
  }
  {
    helpers::Runner r(
      {"/usr/bin/python", "-c" ,"print chr(10).join(['A', 'B', 'C'])"},
      ""
    );
    r.exec();
    assert((r.rc == 0));
    assert((r.out == "A\nB\nC\n"));
    assert((r.err == ""));
  }
  {
    helpers::Runner r(
      {"/usr/bin/bash", "-c" ,"sleep 2"},
      "",
      1
    );
    r.exec();
    assert((r.rc != 0));
    assert((r.out == ""));
    assert((r.err == "Timeout."));
  }
  {
    helpers::Runner r(
      {"/usr/bin/python", "-c" ,"import nonexists"},
      ""
    );
    r.exec();
    assert((r.out == ""));
    assert((r.err == "Traceback (most recent call last):\n  File \"<string>\", line 1, in <module>\nImportError: No module named nonexists\n"));
    assert((r.rc != 0));
  }
  {
    helpers::Runner r("/usr/bin/false", "");
    r.exec();
    assert((r.rc != 0));
    assert((r.out == ""));
    assert((r.err == ""));
  }
  {
    std::string s = "a\nb";
    std::vector<std::string> expected = {"a", "b"};
    auto lines = helpers::splitString(s);
    assert(lines == expected);
  }
  {
    std::string s = "a\nb\n";
    std::vector<std::string> expected = {"a", "b"};
    auto lines = helpers::splitString(s);
    assert(lines == expected);
  }
  {
    std::string s = "a\nb\n\n";
    std::vector<std::string> expected = {"a", "b"};
    auto lines = helpers::splitString(s);
    assert(lines == expected);
  }
  {
    std::string s = "\na\nb\n\n";
    std::vector<std::string> expected = {"a", "b"};
    auto lines = helpers::splitString(s);
    assert(lines == expected);
  }
}
