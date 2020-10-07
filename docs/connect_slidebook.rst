.. contents::

.. _connect_slidebook:

*****************
connect_slidebook
*****************
Rest API calls to control 3i spinning disk microscopes. The 3i Slidebook
software control 3i microscopes. It uses Matlab as macro language. The
macro language is mainly used for image processing. The options to control
the hardware are very limited.

To use this module additional microservices and MatLab code are required.
MatLab receives information about the last image acquire through Slidebook.
The MatLab code communicates by REST API with several microservices:

.. _data_service:

- commands_service: Automation software (via :ref:`connect_slidebook`) post
  commands (experiments). MatLab pulls them and hands information back to
  Slidebook.

- data_service: MatLab posts image and limited meta data. Automation
  Software and other micro-services can get images and meta data.

- imageviewer: Pulls and displays image from ``data-service``. User can
  select positions. Automation Software pulls the selected position for
  further processing.

Slidebook and MatLab
====================
To control 3i Slidebook open Slidebook and configure advanced capture.
Setup a script that calls MatLab code after an image (or a series of images)
was captured.

The MatLab function ``find_location_of_interest`` receives an image from
MatLab and posts the stage position to ``commands_service``. Than it gets
the next experiment in the experiments queue from ``commands_service``.
The script can execute the following actions:

- snap: snap image at current location
- move: move stage and objective in x, y, z. Do not take image.
- move_snap: move stage and objective in x, y, z and take image.
- exit: stop execution. To continue script has to be started manually
  within Slidebook.

.. _commands_service:

commands_service
================
``commands_service`` can be accessed on http://localhost:5000.
The service implements a queue with experiments.
It uses the following API:

- /about, /cmd/about: **get** information about server
- /cmd/experiments: **post** experiment as last entry on queue or
  **get** dictionary with all experiments on queue
- /cmd/experiments/clear: **delete** all experiments from queue
- /cmd/experiments/count: **get** number of experiments on queue
- /cmd/experiments/next: **get** next (oldest) experiment on queue
- /cmd/experiments/{experiment_id}: **get** or **delete** experiment with id
- /cmd/microscope/microscope: **post** information about microscope
- /cmd/recent_position: **post** and **get** most recent position returned
  by microscope

Experiment
==========
An experiment is send as payload when posting or getting data from
/cmd/experiments/\*. It is a dictionary that instructs Slidebook how to
acquire images.

    experiment = server.api.model ('Experiment', {
        'experiment_id': fields.String (description = 'Unique id returned from commands queue'),

        'microscope': fields.String (required = True, min_length = 1, max_length = 200, description='Name of microscope'),

        'number_positions': fields.Integer(required = True, description = 'Number N of positions to image'),

        'stage_locations': fields.List (fields.List(fields.Integer), required = True, description = '(x,y,z) tuples of N imaging positions'),

        'stage_locations_filter': fields.List(fields.Boolean, required = False, description = '(x,y,z) tuples of N True/False filter'),

        'capture_settings': fields.List (fields.String, required = True, description = 'Slidebook experiment names for N positions'),

        'centers_of_interest': fields.List (fields.List(fields.Integer), description = '(x,y,z) tuples of N centers of interest (optional)'),

        'objective':  fields.String (required = True, min_length = 0, max_length = 200, description = 'Name of objective used for imaging'),

        'time_stamp': fields.String(required = True, description = 'Time stamp when request was send'),

        'microscope_action': fields.String (required = True,
         min_length = 1,

         max_length = 20,

         description = '''list of actions microscope should perform:
          snap: take image without moving stage

          move: move without snapping image

          move_snap: move to new position and execute experiment

          exit: exit automation workflow'''),

        'id_counter': fields.Integer(description = 'Counter assigned by service'),

        'status': fields.String (min_length = 0, max_length = 20, description = 'Processing status assigned by service')

    })

.. _connect_slidebook_ConnectMicroscope:

class ConnectMicroscope()
=========================
Class to control 3i hardware through SlideBook software.

.. autoclass:: microscope_automation.slidebook.connect_slidebook.ConnectMicroscope
    :members:
