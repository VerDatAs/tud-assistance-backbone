#  Assistance Backbone for the assistance system developed as part of the VerDatAs project
#  Copyright (C) 2022-2024 TU Dresden (Maximilian Brandt, Sebastian Kucharski)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app
WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . .

RUN chown -R 33:33 /app

USER 33:33

CMD ["python","-u","main.py"]