# Copyright 2025 Silex Data Solutions dba Data Science Technologies, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any

from pydantic import BaseModel


def custom_default(obj: Any) -> Any:
    """
    Custom serialization function for objects that may not be JSON serializable by default.
    This mimics the original default_serialization but is renamed and placed in a different location.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    return str(obj)
