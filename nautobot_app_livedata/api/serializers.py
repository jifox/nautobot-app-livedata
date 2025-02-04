"""Nautobot App Livedata API Serializers."""

# filepath: nautobot_app_livedata/api/serializers.py

from nautobot.dcim.models import Interface
from rest_framework import serializers

from nautobot_app_livedata.utilities.primarydevice import PrimaryDeviceUtils


class LivedataSerializer(serializers.Serializer):
    """Serializer for the Nautobot App Livedata API to return the Managed Device.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/

    This serializer is used to get the managed device for the given object_type
    and ID.

    Properties:

    - pk (UUID): The primary key of the object.
    - object_type (str): The object type to get the managed device for.

    Raises:
    - ValidationError: If the object type is not defined.
    - ValidationError: If the object ID is not defined.
    - ValidationError: If the object_type is not valid.
    - ValidationError: If the object is not found.
    - ValidationError: If the object does not have a primary IP address.
    - ValidationError: If the object state is not Active.
    """

    pk = serializers.UUIDField(required=True, allow_null=False)
    object_type = serializers.CharField(required=True, allow_blank=False)

    queryset = Interface.objects.all()

    def validate(self, attrs):
        """Validate the object type and the device/interface ID."""
        # Check that the object_type is valid
        if "object_type" not in attrs:
            raise serializers.ValidationError("The object type is not defined", code="invalid")
        if "pk" not in attrs:
            raise serializers.ValidationError("The object ID is not defined", code="invalid")
        try:
            result = PrimaryDeviceUtils(object_type=attrs["object_type"], pk=attrs["pk"]).to_dict()
            attrs.update(result)
        except ValueError as err:
            raise serializers.ValidationError(str(err), code="invalid") from err
        return attrs

    def create(self, validated_data):
        """Serializer does not create any objects."""
        raise NotImplementedError

    def update(self, instance, validated_data):
        """Serializer does not update any objects."""
        raise NotImplementedError


class LivedataJobResultSerializer(serializers.Serializer):
    """Serializer for the Nautobot App Livedata API to return the Job Result.

    This serializer is used to get the job result for the given jobresult_id.

    Properties:

    - jobresult_id (UUID): The job result ID of the job that was enqueued.

    Raises:
    - ValidationError: If the job result ID is not defined.
    - ValidationError: If the job result is not found.

    """

    jobresult_id = serializers.UUIDField(required=True, allow_null=False)

    def validate(self, attrs):
        """Validate the job result ID."""
        if "jobresult_id" not in attrs:
            raise serializers.ValidationError("The job result ID is not defined", code="invalid")
        return attrs

    def create(self, validated_data):
        """Serializer does not create any objects."""
        raise NotImplementedError

    def update(self, instance, validated_data):
        """Serializer does not update any objects."""
        raise NotImplementedError
