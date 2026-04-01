// Map partition names to their time limits in hours
const partitionMaxHours = {
  "short":               30,   // 1-06:00:00
  "long":               240,   // 10-00:00:00
  "himem":              240,
  "relion":             240,
  "fraser":             240,
  "brcgel":             240,
  "win":                240,
  "cloudcomp":          240,
  "gpu_short":            4,   // 4:00:00
  "gpu_long":            60,   // 2-12:00:00
  "gpu_relion":         168,   // 7-00:00:00
  "gpu_long_palamara":  168,
  "gpu_long_zhang":     168,
  "gpu_mig_test":         4,
  "gpu_cryosparc":      168,
  "gpu_interactive":     12,
  "gpu_limit":          168,
  "gpu_gh200":         1440,   // 60-00:00:00
  "gpu_a100_80gb":       60,
  "gpu_p100_16gb":       60,
  "gpu_v100_16gb":       60,
  "gpu_v100_32gb":       60,
  "gpu_a100_40gb":       60,
  "gpu_rtx6000_24gb":    60,
  "gpu_rtx8000_48gb":    60,
  "gpu_l4_24gb":         60,
  "gpu_l40s_48gb":       60,
  "gpu_gh200_144gb":     60,
  "gpu_inter":           12,
  "gpu_strubi":         168,
  "gpu_cs":             168,
};

function updateMaxHours() {
  const partition = $("#batch_connect_session_context_auto_queues").val();
  const maxHours  = partitionMaxHours[partition] || 240;
  const hoursField = $("#batch_connect_session_context_bc_num_hours");

  // Update the max attribute
  hoursField.attr("max", maxHours);

  // Clamp the current value if it exceeds the new max
  const currentVal = parseInt(hoursField.val(), 10);
  if (currentVal > maxHours) {
    hoursField.val(maxHours);
  }

  // Update the help text to reflect the limit
  hoursField.closest(".form-group")
    .find(".form-text")
    .text(
      `Maximum runtime in hours for your session. ` +
      `The '${partition}' partition allows up to ${maxHours} hour(s).`
    );
}

$(document).ready(function () {
  // Run on page load to set correct state for cached/default partition
  updateMaxHours();

  // Run whenever the partition changes
  $("#batch_connect_session_context_auto_queues").on("change", updateMaxHours);
});