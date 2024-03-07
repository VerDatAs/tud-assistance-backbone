"""
    Assistance Backbone for the assistance system developed as part of the VerDatAs project
    Copyright (C) 2022-2024 TU Dresden (Sebastian Kucharski)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from loguru import logger

from error.expert_module import LcoNotExistsError
from error.student_module import StudentModelNotExistsError
from model.core.student_module import StudentLcoProgress, StudentModelParameter
from service.db.learning_content_object import read_learning_content_object_by_lco_id, \
    read_learning_content_objects_by_object_id
from service.db.student_model import read_student_model_by_user_id
from service.learning_content_object import get_sub_learning_content_objects
from service.statement import ilias_statement_h5p_object_id_without_sub_content_id


def get_student_lco_progress(user_id: str, lco_id: str = None, object_id: str = None,
                             include_sub_lcos: bool = False) -> StudentLcoProgress:
    if lco_id is None and object_id is None:
        raise AttributeError()

    # TODO: Here a filter of the experiences should be applied instead of loading all experiences
    student_model = read_student_model_by_user_id(user_id)
    if student_model is None:
        raise StudentModelNotExistsError()

    student_lco_progress = StudentLcoProgress.create_with_default_parameters(user_id)

    student_lco_progress.progress = list(
        filter(lambda experience: experience.object_id == object_id if lco_id is None else experience.lco_id == lco_id,
               student_model.experiences))
    if not include_sub_lcos:
        return student_lco_progress

    if lco_id is not None and object_id is not None:
        lco = read_learning_content_object_by_lco_id(lco_id)
        if lco is None:
            raise LcoNotExistsError()
        if lco.object_id != object_id:
            raise AttributeError()
    elif lco_id is not None and object_id is None:
        lco = read_learning_content_object_by_lco_id(lco_id)
        if lco is None:
            raise LcoNotExistsError()
    elif lco_id is None and object_id is not None:
        lco = None
        lcos = read_learning_content_objects_by_object_id(object_id)
        if lcos is None or not lcos:
            logger.info("Statement for unknown LCO received")
        elif len(lcos) != 1:
            logger.info("ObjectId of the received statement applies to more than one LCO")
        else:
            lco = lcos[0]
    else:
        return student_lco_progress

    if lco is None:
        return student_lco_progress

    sub_lco_object_ids_to_experiences = {sub_lco.object_id: [] for sub_lco in get_sub_learning_content_objects(lco)}
    for experience in student_model.experiences:
        if ilias_statement_h5p_object_id_without_sub_content_id(
                experience.object_id) not in sub_lco_object_ids_to_experiences:
            continue
        sub_lco_object_ids_to_experiences[
            ilias_statement_h5p_object_id_without_sub_content_id(experience.object_id)] += [experience]
    sub_lco_progress = []
    for sub_lco_object_id, experiences_list in sub_lco_object_ids_to_experiences.items():
        # TODO: Here another element should be used
        sub_lco_progress.append(
            StudentModelParameter.create_with_default_parameters(sub_lco_object_id, experiences_list))

    student_lco_progress.sub_lco_progress = sub_lco_progress
    return student_lco_progress
