# Written by Dmitry Chirikov <dmitry@chirikov.ru>
# Created in ClusterVision <infonl@clustervision.com>
#
# This file is part of Luna, cluster provisioning tool
# https://github.com/clustervision/luna
#
# This file is part of Luna.

# Luna is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Luna is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Luna.  If not, see <http://www.gnu.org/licenses/>.

"""
Main flask app export
"""
from .lunad import APP as app  # noqa # pylint: disable=unused-import
