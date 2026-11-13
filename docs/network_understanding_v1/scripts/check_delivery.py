"""Check teaching artifacts and all referenced local paths."""
import sys
sys.dont_write_bytecode=True
import hashlib,json,re
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as s:
        for b in iter(lambda:s.read(4*1024*1024),b""):h.update(b)
    return h.hexdigest()
baseline=read(HERE/"reports/SOURCE_BASELINE.json")
changed=[r for r,v in baseline.items() if sha(ROOT/r)!=v["sha256"]]
broken=[];links=0
mds=sorted(HERE.glob("*.md"))
for p in mds:
    t=p.read_text(encoding="utf-8")
    assert "\ufffd" not in t,p
    assert t.count("~~~")%2==0,p
    for target in re.findall(r"\]\(([^)\n]+)\)",t):
        target=target.strip("<>")
        if not re.match(r"^[A-Z]:[/\\]",target):continue
        links+=1
        m=re.search(r":(\d+)$",target)
        f=Path(target[:m.start()] if m else target)
        if not f.exists():broken.append(dict(document=p.name,target=target))
        elif m and int(m.group(1))>len(f.read_bytes().splitlines()):
            broken.append(dict(document=p.name,target=target,error="line out of bounds"))
images=[]
for p in sorted((HERE/"figures").glob("*.png")):
    with Image.open(p) as im:
        im.verify()
    with Image.open(p) as im:images.append(dict(path=p.name,width=im.width,height=im.height))
audit=read(HERE/"reports/SOURCE_AUDIT.json")
theory=read(HERE/"reports/THEORY_DEMO.json")
trace=read(HERE/"reports/POINT_TRACE.json")
identifiability=read(HERE/"reports/IDENTIFIABILITY_DEMO.json")
interactive=read(HERE/"reports/INTERACTIVE_CHECK.json")
features=read(HERE/"reports/FEATURE_WALKTHROUGH.json")
training_guard=read(HERE/"reports/TRAINING_GUARD_WALKTHROUGH.json")
fixed_hardware=read(HERE/"reports/FIXEDPOINT_HARDWARE_WALKTHROUGH.json")
evidence=read(HERE/"reports/EVIDENCE_WALKTHROUGH.json")
learned=read(HERE/"reports/LEARNED_RULE_WALKTHROUGH.json")
display=read(HERE/"reports/DISPLAY_MAPPING_WALKTHROUGH.json")
quantization=read(HERE/"reports/QUANTIZATION_THEORY_WALKTHROUGH.json")
collision=read(HERE/"reports/HARMONIC_COLLISION_WALKTHROUGH.json")
network_learning=read(HERE/"reports/NETWORK_LEARNING_WALKTHROUGH.json")
network_learning_ui=read(HERE/"reports/NETWORK_LEARNING_INTERACTIVE_CHECK.json")
provenance=read(HERE/"reports/DATA_PROVENANCE_WALKTHROUGH.json")
parent_query=read(HERE/"reports/PARENT_QUERY_WALKTHROUGH.json")
loss_gradient=read(HERE/"reports/LOSS_GRADIENT_WALKTHROUGH.json")
original_comparison=read(HERE/"reports/ORIGINAL_SCALAR_COMPARISON.json")
zero_convention=read(HERE/"reports/ZERO_CONVENTION_WALKTHROUGH.json")
gain_limits=read(HERE/"reports/GAIN_LIMITS_WALKTHROUGH.json")
harmonic_ui=read(HERE/"reports/HARMONIC_QUERY_INTERACTIVE_CHECK.json")
normalization=read(HERE/"reports/NORMALIZATION_WALKTHROUGH.json")
weak_information=read(HERE/"reports/WEAK_INFORMATION_WALKTHROUGH.json")
encoding=read(HERE/"reports/ENCODING_WALKTHROUGH.json")
gain_error=read(HERE/"reports/GAIN_ERROR_WALKTHROUGH.json")
architecture=read(HERE/"reports/NETWORK_ARCHITECTURE_FIGURE.json")
architecture_review=read(HERE/"reports/NETWORK_ARCHITECTURE_REVIEW.json")
ambiguity_risk=read(HERE/"reports/AMBIGUITY_RISK_WALKTHROUGH.json")
feature_expansion=read(HERE/"reports/FEATURE_EXPANSION_WALKTHROUGH.json")
method_chapter=read(HERE/"reports/METHOD_CHAPTER_REVIEW.json")
point_reference=read(HERE/"reports/POINT_REFERENCE_WALKTHROUGH.json")
composed_guard=read(HERE/"reports/COMPOSED_GUARD_WALKTHROUGH.json")
error_partition=read(HERE/"reports/SAVED_FRAME_ERROR_PARTITION.json")
decision_roles=read(HERE/"reports/HARMONIC_DECISION_ROLES.json")
training_sampling=read(HERE/"reports/TRAINING_SAMPLING_WALKTHROUGH.json")
spectral_shift=read(HERE/"reports/SPECTRAL_SHIFT_WALKTHROUGH.json")
saved_threshold=read(HERE/"reports/SAVED_THRESHOLD_WALKTHROUGH.json")
bounded_oracle=read(HERE/"reports/BOUNDED_ORACLE_WALKTHROUGH.json")
aperture_sidelobe=read(HERE/"reports/APERTURE_SIDELOBE_WALKTHROUGH.json")
loss_scale=read(HERE/"reports/LOSS_SCALE_WALKTHROUGH.json")
dependency_support=read(HERE/"reports/DEPENDENCY_SUPPORT_WALKTHROUGH.json")
relative_sign_information=read(HERE/"reports/RELATIVE_SIGN_INFORMATION.json")
uniform_gain=read(HERE/"reports/UNIFORM_GAIN_WALKTHROUGH.json")
saved_score=read(HERE/"reports/SAVED_SCORE_SUPERVISION.json")
feature_points=features["actual_point_checks"]
toy=features["toy_child_gate"]
checks=dict(
    frozen_sources_unchanged=not changed,
    local_links_resolve=not broken,
    complete_teaching_documents={p.name.split("_",1)[0] for p in HERE.glob("[0-9][0-9]_*.md")}=={f"{i:02}" for i in range(22)} and len(list(HERE.glob("[0-9][0-9]_*.md")))==22,
    eight_scientific_figures=len(images)==8,
    source_audit_pass=audit["status"]=="PASS",
    mathematical_demo_pass=theory["status"]=="PASS",
    relative_ambiguity_counterexample_pass=identifiability["status"]=="PASS" and identifiability["two_dimensional_same_quantized_input"],
    interactive_runtime_and_layout=interactive["status"]=="PASS" and not interactive["browserErrors"],
    four_point_traces_match_existing=trace["status"]=="PASS" and len(trace["rows"])==4 and all(r["matches_existing_expected"] for r in trace["rows"]),
    four_point_features_match_existing=features["status"]=="PASS" and len(feature_points)==4 and all(r["code_features_exact"] and r["existing_neural_vector_exact"] for r in feature_points),
    child_gate_teaching_example=len(toy)==2 and toy[0]["child_center_q12"]==toy[1]["child_center_q12"] and toy[0]["child_gated_support_q12"]==toy[0]["child_center_q12"] and toy[1]["child_gated_support_q12"]==0,
    feature_walkthrough_preserves_scope=not features["neural_parameters_modified"] and not features["neural_quality_test_run"] and not features["board_accessed"],
    training_snapshot_algebra_matches=training_guard["status"]=="PASS" and training_guard["training_source_matches_selected_config"] and training_guard["source_loss_matches_independent_algebra"] and abs(training_guard["numpy_total"]-training_guard["executed_source_totals"]["float64"])<1e-10,
    four_guard_points_match_existing=len(training_guard["existing_guard_points"])==4 and all(r["existing_trace_and_output_exact"] for r in training_guard["existing_guard_points"]),
    training_guard_teaching_preserves_scope=not any(training_guard[k] for k in ["neural_parameters_modified","training_run","new_quality_test_run","board_accessed"]),
    hls_pc_and_float_constants_match=fixed_hardware["status"]=="PASS" and all(fixed_hardware["frozen_constants_match_pc"].values()) and all(fixed_hardware["float_weight_rounding_matches_hls"].values()),
    fixed_four_points_match_existing=len(fixed_hardware["four_point_integer_replay"])==4 and all(r["existing_trace_exact"] for r in fixed_hardware["four_point_integer_replay"]),
    fixed_width_and_clock_evidence=fixed_hardware["partial_accumulator_rounding_margin_verified"] and fixed_hardware["power_scaling"]["maximum_scaled_bit_length"]<=fixed_hardware["power_scaling"]["hls_temporary_bits"] and fixed_hardware["frozen_bd_expected_peers_verified"] and fixed_hardware["clocks"]["actual_core_mhz"]==100 and fixed_hardware["clocks"]["actual_controller_mhz"]==250,
    fixed_walkthrough_preserves_scope=not any(fixed_hardware[k] for k in ["neural_parameters_modified","hls_built","full_frame_inference_run","new_quality_test_run","board_accessed"]),
    existing_evidence_metrics_match=evidence["status"]=="PASS" and evidence["arrays_checked"]==22 and len(evidence["rows"])==22 and all(r["saved_arrays_match_report"] for r in evidence["rows"]) and evidence["all_existing_metrics_match"] and evidence["aggregation_matches_original_summary"],
    evidence_groups_explicit=evidence["groups"]["synthetic_512"]["known_targets"]==64 and evidence["groups"]["synthetic_512"]["known_weak_targets"]==48 and evidence["groups"]["field_temporal_128"]["records"]==6 and evidence["known_target_summary"]["known_targets"]==120,
    evidence_quality_boundaries_preserved=evidence["quality_status_preserved"]=="FAIL" and evidence["weak_correction_status_preserved"]=="PASS" and evidence["groups"]["synthetic_512"]["numeric_reference_peak_drops"]==1,
    evidence_walkthrough_preserves_scope=not any(evidence[k] for k in ["neural_parameters_modified","new_inference_run","new_holdout_opened","training_run","board_accessed"]),
    learned_four_points_replay_exact=learned["status"]=="PASS" and len(learned["rows"])==4 and all(r["source_trace_exact"] and r["exact_identity"]["exact_match"] for r in learned["rows"]),
    learned_decomposition_and_same_center=learned["exact_integer_decomposition_verified"] and learned["same_center_different_raw_gain_verified"] and all(r["active_pattern_matches_ideal_real"] and r["exact_identity"]["feature_sum_numerator"]+r["exact_identity"]["effective_bias_numerator"]+r["exact_identity"]["propagated_rounding_numerator"]==r["score_q16"]*(1<<48) for r in learned["rows"]),
    learned_sources_still_match=all(sha(ROOT/p)==v for p,v in learned["source_sha256"].items()),
    learned_walkthrough_preserves_scope=not any(learned[k] for k in ["neural_parameters_modified","training_run","full_frame_inference_run","new_quality_test_run","new_holdout_opened","board_accessed"]),
    display_current_sources_match=display["status"]=="PASS" and all(sha(ROOT/p)==v for p,v in display["source_sha256"].items()) and all(v["exists"] and v["sha_equal"] and sha(ROOT/p)==sha(ROOT/v["path"]) for p,v in display["generated_source_copies"].items()),
    display_mapping_and_pixel_checks=display["table_matches_existing_mapper"] and display["existing_parameter_and_ccid_match"] and len(display["pixel_address_checks"])==7 and all(r["scalar_matches_existing_mapper"] for r in display["pixel_address_checks"]) and len(display["existing_points"])==4 and all(r["existing_output_matches"] for r in display["existing_points"]) and len(display["existing_visible_pixel_traces"])==3 and all(r["stored_example_output_exact"] for r in display["existing_visible_pixel_traces"]),
    display_interpretation_counterexamples=display["byte_display"]["monotone"] is False and display["byte_display"]["counterexample"]["input_power"]>display["byte_display"]["counterexample"]["output_power"] and display["byte_display"]["counterexample"]["input_byte"]<display["byte_display"]["counterexample"]["output_byte"] and display["mapped_metric_weighting_example"]["rd_enhanced_sse"]<display["mapped_metric_weighting_example"]["rd_baseline_sse"] and display["mapped_metric_weighting_example"]["mapped_enhanced_sse"]>display["mapped_metric_weighting_example"]["mapped_baseline_sse"] and display["coherent_phase_ambiguity_example"]["same_phase_sum_power"]!=display["coherent_phase_ambiguity_example"]["opposite_phase_sum_power"],
    display_walkthrough_preserves_scope=not any(display[k] for k in ["neural_parameters_modified","training_run","fft_run","feature_extraction_run","full_frame_neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    quantization_theory_mathematics_verified=quantization["status"]=="PASS" and all(quantization["checks"].values()) and quantization["frozen_files_checked"]==26 and not quantization["changed_sources"],
    quantization_teaching_preserves_scope=not any(quantization[k] for k in ["model_parameters_modified","training_run","radar_data_fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    harmonic_collision_theory_verified=collision["status"]=="PASS" and all(collision["checks"].values()) and collision["frozen_files_checked"]==26 and not collision["changed_sources"] and all(sha(ROOT/p)==v for p,v in collision["source_sha256"].items()),
    harmonic_collision_preserves_scope=not any(collision[k] for k in ["model_parameters_modified","training_run","radar_data_fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    network_learning_records_and_algebra=network_learning["status"]=="PASS" and all(network_learning["checks"].values()) and len(network_learning["visual_payload"]["points"])==2 and all(sha(ROOT/p)==v for p,v in network_learning["source_sha256"].items()),
    network_learning_visual_matches_record=sha(Path(network_learning["visual_path"]))==network_learning["visual_sha256"] and network_learning_ui["status"]=="PASS" and len(network_learning_ui["rows"])==30 and not network_learning_ui["browserErrors"] and network_learning_ui["savedStateRestoration"] and network_learning_ui["pairedReferenceCompared"],
    network_learning_preserves_scope=not any(network_learning[k] for k in ["model_parameters_modified","training_run","fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    training_data_and_checkpoint_provenance_verified=provenance["status"]=="PASS" and all(provenance["checks"].values()) and len(provenance["training_records"])==62 and len(provenance["raw_payload_audit"]["frames"])==14 and len(provenance["checkpoints"])==7 and all(sha(ROOT/p)==v for p,v in provenance["source_sha256"].items()),
    provenance_preserves_scope=not any(provenance[k] for k in ["model_parameters_modified","training_run","fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_quality_holdout_evaluated","hardware_built","board_accessed"]),
    parent_query_geometry_and_maximum_verified=parent_query["status"]=="PASS" and all(parent_query["checks"].values()) and sum(row["coordinates_checked"] for row in parent_query["axes"])==3072 and [row["encoded_support_points"] for row in parent_query["parent_query_geometry"]]==[81,225] and all(sha(ROOT/p)==v for p,v in parent_query["source_sha256"].items()),
    parent_query_preserves_scope=not any(parent_query[k] for k in ["model_parameters_modified","training_run","fft_run","radar_feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    loss_gradient_snapshot_and_shared_algebra_verified=loss_gradient["status"]=="PASS" and all(loss_gradient["checks"].values()) and len(loss_gradient["examples"])==10 and len(loss_gradient["per_term_maximum_derivative_error"])==8 and loss_gradient["total_maximum_derivative_error"]<1e-10 and loss_gradient["maximum_finite_difference_error"]<1e-7 and all(sha(ROOT/p)==v for p,v in loss_gradient["source_sha256"].items()),
    loss_gradient_preserves_scope=loss_gradient["constructed_score_autograd_run"] and not any(loss_gradient[k] for k in ["model_instantiated","model_backward_run","optimizer_run","model_parameters_modified","training_run","fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    original_and_scalar_head_algebra_verified=original_comparison["status"]=="PASS" and all(original_comparison["checks"].values()) and original_comparison["algebra_pairs_checked"]==6006 and not original_comparison["toy_off_color_curve"]["has_exact_scalar_preimage_on_toy_curve"] and all(sha(ROOT/p)==v for p,v in original_comparison["source_sha256"].items()),
    original_comparison_preserves_scope=not any(original_comparison[k] for k in ["model_instantiated","model_parameters_modified","training_run","fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    zero_convention_and_padding_algebra_verified=zero_convention["status"]=="PASS" and all(zero_convention["checks"].values()) and len(zero_convention["distributions"])==4 and zero_convention["hypothetical_padding_error"]["no_claim_this_error_exists_in_current_runtime"] and all(sha(ROOT/p)==v for p,v in zero_convention["source_sha256"].items()),
    zero_convention_preserves_scope=zero_convention["constructed_direct_dft_run"] and not any(zero_convention[k] for k in ["radar_data_fft_run","model_instantiated","model_parameters_modified","quantizer_rule_modified","training_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    gain_limits_contrast_and_existing_points_verified=gain_limits["status"]=="PASS" and all(gain_limits["checks"].values()) and len(gain_limits["gain_table"])==6 and len(gain_limits["existing_points"])==4 and len(gain_limits["ideal_single_tone_harmonic_limits"])==2 and all(sha(ROOT/p)==v for p,v in gain_limits["source_sha256"].items()),
    gain_limits_preserves_scope=not any(gain_limits[k] for k in ["model_instantiated","model_parameters_modified","training_run","fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    harmonic_query_visual_verified=harmonic_ui["status"]=="PASS" and sha(Path(harmonic_ui["visual_path"]))==harmonic_ui["visual_sha256"] and all(sha(ROOT/p)==v for p,v in harmonic_ui["source_sha256"].items()) and len(harmonic_ui["geometry_cases"])==32 and len(harmonic_ui["layout_cases"])==24 and not harmonic_ui["browserErrors"] and all(harmonic_ui[k] for k in ["full_support_sets_match_independent_modular_inverse","existing_record_matches","input_bounds_and_presets","saved_state_restoration","legend_visibility","pointer_selection"]),
    harmonic_query_preserves_scope=not any(harmonic_ui[k] for k in ["model_parameters_modified","training_run","radar_fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","board_accessed"]),
    normalization_scale_and_anchor_algebra_verified=normalization["status"]=="PASS" and all(normalization["checks"].values()) and normalization["sign_scale_cases"]==867 and len(normalization["normalization_cases"])==16 and normalization["exact_scale_identity_cases"]==144 and all(sha(ROOT/p)==v for p,v in normalization["source_sha256"].items()),
    normalization_preserves_scope=normalization["constructed_normalization_run"] and normalization["constructed_guard_run"] and not any(normalization[k] for k in ["model_instantiated","model_parameters_modified","training_run","fft_run","full_feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    weak_information_probability_and_expansion_verified=weak_information["status"]=="PASS" and all(weak_information["checks"].values()) and len(weak_information["cdf_cases"])==9 and len(weak_information["complex_tone_cases"])==10 and all(sha(ROOT/p)==v for p,v in weak_information["source_sha256"].items()),
    weak_information_preserves_scope=weak_information["deterministic_mathematical_quadrature_run"] and not any(weak_information[k] for k in ["random_sampling_run","model_instantiated","model_parameters_modified","training_run","radar_fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    encoding_means_gates_and_thresholds_verified=encoding["status"]=="PASS" and all(encoding["checks"].values()) and encoding["ideal_grid_points"]==1001 and len(encoding["window_examples"])==5 and len(encoding["specified_flat_window_thresholds"])==3 and all(sha(ROOT/p)==v for p,v in encoding["source_sha256"].items()),
    encoding_preserves_scope=encoding["constructed_algebra_run"] and not any(encoding[k] for k in ["model_instantiated","model_parameters_modified","training_run","radar_fft_run","full_feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    gain_error_conditions_and_metric_difference_verified=gain_error["status"]=="PASS" and all(gain_error["checks"].values()) and gain_error["exact_grid_cases"]==364 and gain_error["known_reference_optimum_cases"]==52 and len(gain_error["existing_points"])==4 and all(sha(ROOT/p)==v for p,v in gain_error["source_sha256"].items()),
    gain_error_preserves_scope=gain_error["exact_constructed_algebra_run"] and not any(gain_error[k] for k in ["model_instantiated","model_parameters_modified","training_run","radar_fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    network_architecture_matches_frozen_sources=architecture["status"]=="PASS" and architecture["parameters"]==1857 and architecture["weights"]==1808 and architecture["biases"]==49 and sum(architecture["feature_groups"].values())==40 and [row["parameters"] for row in architecture["layers"]]==[1312,528,17] and architecture["all_1857_parameters_in_shared_mlp"] and not architecture["inference_guards_trained_end_to_end"] and not architecture["reference_used_in_inference"] and all(sha(ROOT/p)==v for p,v in architecture["source_sha256"].items()),
    network_architecture_figure_reviewed=architecture_review["status"]=="PASS" and architecture_review["labels_and_arrows_viewed"] and architecture_review["revised_heading_clear_of_power_path"] and architecture_review["svg_valid"] and architecture_review["svg_is_vector_without_raster_images"] and sha(HERE/"reports/NETWORK_ARCHITECTURE_FIGURE.json")==architecture_review["figure_report_sha256"] and not architecture["text_bounds_outside"] and not architecture["text_outside_blocks"] and not architecture["text_collisions"] and all(sha(ROOT/p)==v for p,v in architecture["output_files"].items()),
    network_architecture_preserves_scope=not any(architecture[k] for k in ["model_instantiated","model_parameters_modified","training_run","radar_fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]) and (HERE/"网络结构总览与逐步讲稿.md").is_file(),
    user_theory_priority_recorded="单比特失真与恢复的理论" in (HERE/"00_阅读入口.md").read_text(encoding="utf-8") and "用户明确选择" in (HERE/"学习进度.md").read_text(encoding="utf-8"),
    ambiguity_risk_decomposition_and_examples_verified=ambiguity_risk["status"]=="PASS" and all(ambiguity_risk["checks"].values()) and ambiguity_risk["distributions_checked"]==8 and ambiguity_risk["risk_comparisons"]==56 and all(sha(ROOT/p)==v for p,v in ambiguity_risk["source_sha256"].items()) and sha(HERE/"scripts/ambiguity_risk_walkthrough.py")==ambiguity_risk["script_sha256"],
    ambiguity_risk_preserves_scope=ambiguity_risk["exact_constructed_algebra_run"] and not any(ambiguity_risk[k] for k in ["model_instantiated","model_parameters_modified","training_run","radar_fft_run","feature_extraction_run","neural_inference_run","actual_guard_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    feature_expansion_formulas_and_retained_information_verified=feature_expansion["status"]=="PASS" and all(feature_expansion["checks"].values()) and feature_expansion["constructed_vectors"]==12 and feature_expansion["existing_vectors"]==4 and feature_expansion["expansion_vectors"]==16 and feature_expansion["retained_base_channels"]==list(range(8))+list(range(16,40)) and all(sha(ROOT/p)==v for p,v in feature_expansion["source_sha256"].items()) and sha(HERE/"scripts/feature_expansion_walkthrough.py")==feature_expansion["script_sha256"],
    feature_expansion_preserves_scope=feature_expansion["constructed_feature_augmentation_run"] and not any(feature_expansion[k] for k in ["model_instantiated","neural_layer_run","model_backward_run","model_parameters_modified","training_run","radar_fft_run","full_feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    method_chapter_review_versions_match=method_chapter["status"]=="PASS" and method_chapter["manual_semantic_review_complete"] and len(method_chapter["sections"])==8 and sha(ROOT/method_chapter["draft_path"])==method_chapter["draft_sha256"] and all(sha(ROOT/p)==v for p,v in method_chapter["source_sha256"].items()) and all(sha(ROOT/p)==v for p,v in method_chapter["evidence_sha256"].items()),
    method_chapter_preserves_scope=method_chapter["full_quality_status_preserved"]=="FAIL" and not method_chapter["formal_publication_ready_claimed"] and not any(method_chapter[k] for k in ["new_novelty_review_run","model_instantiated","neural_inference_run","training_run","new_quality_test_run","new_holdout_opened","model_parameters_modified","hardware_built","board_accessed"]),
    existing_point_references_and_stage_errors_verified=point_reference["status"]=="PASS" and all(point_reference["checks"].values()) and len(point_reference["point_rows"])==4 and len(point_reference["known_synthetic_target_rows"])==2 and point_reference["record_id"]=="confirm_synth_116013_512" and all(sha(ROOT/p)==v for p,v in point_reference["source_sha256"].items()) and sha(HERE/"scripts/point_reference_walkthrough.py")==point_reference["script_sha256"],
    existing_point_reference_preserves_scope=point_reference["existing_saved_point_reference_comparison_run"] and point_reference["scalar_power_arithmetic_run"] and point_reference["original_quality_status_preserved"]=="FAIL" and not any(point_reference[k] for k in ["model_instantiated","neural_layer_run","neural_inference_run","model_parameters_modified","training_run","radar_fft_run","feature_extraction_run","guard_run","new_quality_test_run","new_holdout_opened","new_dataset_generated","hardware_built","board_accessed"]),
    composed_guard_gain_path_algebra_verified=composed_guard["status"]=="PASS" and all(composed_guard["checks"].values()) and composed_guard["fixed_mask_and_compactness_cases"]==65 and composed_guard["quartic_cases"]==5 and composed_guard["full_restore_raw_gain_interval"][1]==1 and composed_guard["threshold_applies_only_if_both_masks_and_full_compactness_hold"] and all(sha(ROOT/p)==v for p,v in composed_guard["source_sha256"].items()) and sha(HERE/"scripts/composed_guard_walkthrough.py")==composed_guard["script_sha256"],
    composed_guard_preserves_scope=composed_guard["constructed_gain_map_algebra_run"] and not any(composed_guard[k] for k in ["model_instantiated","model_parameters_modified","training_run","radar_fft_run","feature_extraction_run","neural_inference_run","full_guard_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    existing_frame_error_partition_verified=error_partition["status"]=="PASS" and all(error_partition["checks"].values()) and error_partition["record_id"]=="confirm_synth_116013_512" and len(error_partition["regions"])==3 and sum(r["pixels"] for r in error_partition["regions"])==1024*512 and all(sha(ROOT/p)==v for p,v in error_partition["source_sha256"].items()) and sha(HERE/"scripts/saved_frame_error_partition.py")==error_partition["script_sha256"],
    existing_frame_error_partition_preserves_scope=error_partition["saved_frame_metric_accounting_run"] and error_partition["original_full_quality_status_preserved"]=="FAIL" and not any(error_partition[k] for k in ["model_instantiated","neural_inference_run","feature_extraction_run","guard_run","radar_fft_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","new_dataset_generated","hardware_built","board_accessed"]),
    harmonic_features_gain_and_protection_roles_verified=decision_roles["status"]=="PASS" and all(decision_roles["checks"].values()) and len(decision_roles["ratio_cases"])==78 and len(decision_roles["point_rows"])==4 and all(sha(ROOT/p)==v for p,v in decision_roles["source_sha256"].items()) and sha(HERE/"scripts/harmonic_decision_roles.py")==decision_roles["script_sha256"],
    harmonic_decision_roles_preserve_scope=decision_roles["constructed_ratio_algebra_run"] and decision_roles["saved_point_explanation_run"] and decision_roles["original_full_quality_status_preserved"]=="FAIL" and not any(decision_roles[k] for k in ["model_instantiated","neural_inference_run","feature_extraction_run","guard_run","radar_fft_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    training_sampling_and_normalization_algebra_verified=training_sampling["status"]=="PASS" and all(training_sampling["checks"].values()) and training_sampling["entries_per_record"]==22528 and len(training_sampling["specified_mask_example"]["rows"])==7 and len(training_sampling["specified_batch_example"]["rows"])==4 and all(sha(ROOT/p)==v for p,v in training_sampling["source_sha256"].items()) and sha(HERE/"scripts/training_sampling_walkthrough.py")==training_sampling["script_sha256"],
    training_sampling_preserves_scope=training_sampling["exact_probability_algebra_run"] and training_sampling["original_full_quality_status_preserved"]=="FAIL" and training_sampling["actual_fixed_pool_probabilities_not_reconstructed"] and not any(training_sampling[k] for k in ["radar_data_read","sampling_run","training_pool_built","model_instantiated","training_run","optimizer_run","neural_inference_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    spectral_coordinate_and_child_shift_examples_verified=spectral_shift["status"]=="PASS" and all(spectral_shift["checks"].values()) and len(spectral_shift["examples"])==10 and len(spectral_shift["axes"])==2 and all(sha(ROOT/p)==v for p,v in spectral_shift["source_sha256"].items()) and sha(HERE/"scripts/spectral_shift_walkthrough.py")==spectral_shift["script_sha256"],
    spectral_shift_preserves_scope=spectral_shift["constructed_child_feature_run"] and spectral_shift["original_full_quality_status_preserved"]=="FAIL" and not any(spectral_shift[k] for k in ["radar_data_read","radar_fft_run","full_feature_extraction_run","model_instantiated","neural_inference_run","guard_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    saved_threshold_accounts_and_scalar_arithmetic_verified=saved_threshold["status"]=="PASS" and all(saved_threshold["checks"].values()) and len(saved_threshold["thresholds"])==4 and saved_threshold["input_nonzero"]==saved_threshold["output_nonzero"]==524288 and all(sha(ROOT/p)==v for p,v in saved_threshold["source_sha256"].items()) and sha(HERE/"scripts/saved_threshold_walkthrough.py")==saved_threshold["script_sha256"],
    saved_threshold_preserves_scope=saved_threshold["saved_frame_threshold_accounting_run"] and saved_threshold["scalar_power_arithmetic_run"] and saved_threshold["original_full_quality_status_preserved"]=="FAIL" and not any(saved_threshold[k] for k in ["model_instantiated","neural_inference_run","feature_extraction_run","guard_run","radar_fft_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    bounded_reference_relaxation_verified=bounded_oracle["status"]=="PASS" and all(bounded_oracle["checks"].values()) and bounded_oracle["record_id"]=="confirm_synth_116013_512" and sum(r["pixels"] for r in bounded_oracle["regions"])==524288 and all(sha(ROOT/p)==v for p,v in bounded_oracle["source_sha256"].items()) and sha(HERE/"scripts/bounded_oracle_walkthrough.py")==bounded_oracle["script_sha256"],
    bounded_reference_relaxation_preserves_scope=bounded_oracle["saved_frame_reference_relaxation_run"] and bounded_oracle["original_full_quality_status_preserved"]=="FAIL" and not any(bounded_oracle[k] for k in ["model_instantiated","neural_inference_run","feature_extraction_run","guard_run","radar_fft_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    finite_observation_sidelobe_math_verified=aperture_sidelobe["status"]=="PASS" and all(aperture_sidelobe["checks"].values()) and len(aperture_sidelobe["rows"])==2 and aperture_sidelobe["maximum_closed_form_error"]<1e-13 and all(sha(ROOT/p)==v for p,v in aperture_sidelobe["source_sha256"].items()) and sha(HERE/"scripts/aperture_sidelobe_walkthrough.py")==aperture_sidelobe["script_sha256"],
    finite_observation_teaching_preserves_scope=aperture_sidelobe["constructed_direct_dft_run"] and aperture_sidelobe["original_full_quality_status_preserved"]=="FAIL" and not any(aperture_sidelobe[k] for k in ["radar_data_read","radar_fft_run","feature_extraction_run","model_instantiated","neural_inference_run","guard_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    training_loss_scale_and_source_derivatives_verified=loss_scale["status"]=="PASS" and all(loss_scale["checks"].values()) and len(loss_scale["rows"])==2 and abs(loss_scale["weak_to_strong_absolute_gradient_ratios"]["amplitude_squared"]-1e-4)<1e-16 and all(sha(ROOT/p)==v for p,v in loss_scale["source_sha256"].items()) and sha(HERE/"scripts/loss_scale_walkthrough.py")==loss_scale["script_sha256"],
    loss_scale_teaching_preserves_scope=loss_scale["constructed_score_autograd_run"] and loss_scale["original_full_quality_status_preserved"]=="FAIL" and not any(loss_scale[k] for k in ["model_instantiated","model_backward_run","optimizer_run","training_run","model_parameters_modified","radar_data_read","radar_fft_run","feature_extraction_run","neural_inference_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    encoded_dependency_sets_and_original_cnn_topology_verified=dependency_support["status"]=="PASS" and all(dependency_support["checks"].values()) and len(dependency_support["rows"])==7 and dependency_support["rows"][0]["union_encoded_positions"]==585 and dependency_support["delivered_cnn_receptive_field_widths"]["h"]==21 and all(sha(ROOT/p)==v for p,v in dependency_support["source_sha256"].items()) and sha(HERE/"scripts/dependency_support_walkthrough.py")==dependency_support["script_sha256"],
    dependency_support_teaching_preserves_scope=dependency_support["coordinate_support_enumeration_run"] and dependency_support["original_full_quality_status_preserved"]=="FAIL" and not any(dependency_support[k] for k in ["radar_data_read","radar_fft_run","full_feature_extraction_run","model_instantiated","neural_layer_run","neural_inference_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    finite_sign_cells_and_ideal_power_ambiguity_verified=relative_sign_information["status"]=="PASS" and all(relative_sign_information["checks"].values()) and len(relative_sign_information["rows"])==6 and relative_sign_information["power_only_ambiguity"]["exact_circular_shift_samples"]==11 and all(sha(ROOT/p)==v for p,v in relative_sign_information["source_sha256"].items()) and sha(HERE/"scripts/relative_sign_information.py")==relative_sign_information["script_sha256"],
    relative_sign_information_teaching_preserves_scope=relative_sign_information["constructed_direct_dft_run"] and relative_sign_information["original_full_quality_status_preserved"]=="FAIL" and not any(relative_sign_information[k] for k in ["radar_data_read","radar_fft_run","model_instantiated","neural_inference_run","feature_extraction_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    existing_frame_uniform_gain_optimum_verified=uniform_gain["status"]=="PASS" and all(uniform_gain["checks"].values()) and uniform_gain["record_id"]=="confirm_synth_116013_512" and len(uniform_gain["point_rows"])==4 and uniform_gain["uniform_oracle"]["uses_reference"] and all(sha(ROOT/p)==v for p,v in uniform_gain["source_sha256"].items()) and sha(HERE/"scripts/uniform_gain_walkthrough.py")==uniform_gain["script_sha256"],
    uniform_gain_teaching_preserves_scope=uniform_gain["saved_frame_uniform_gain_accounting_run"] and uniform_gain["original_full_quality_status_preserved"]=="FAIL" and not any(uniform_gain[k] for k in ["model_instantiated","neural_inference_run","feature_extraction_run","guard_run","radar_fft_run","training_run","model_parameters_modified","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    user_network_only_scope_recorded="只针对网络的情况，对于部署后续有需要再说" in (HERE/"AGENTS.md").read_text(encoding="utf-8"),
    saved_score_head_supervision_matches_source=saved_score["status"]=="PASS" and all(saved_score["checks"].values()) and len(saved_score["rows"])==3 and all(sha(ROOT/p)==v for p,v in saved_score["source_sha256"].items()) and sha(HERE/"scripts/saved_score_supervision.py")==saved_score["script_sha256"],
    saved_score_explanation_preserves_scope=saved_score["constructed_single_point_head_autograd_run"] and saved_score["original_full_quality_status_preserved"]=="FAIL" and not any(saved_score[k] for k in ["model_instantiated","model_backward_run","optimizer_run","training_run","model_parameters_modified","neural_inference_run","radar_fft_run","feature_extraction_run","new_quality_test_run","new_holdout_opened","hardware_built","board_accessed"]),
    curated_reading_entry_and_original_index_preserved=sha(HERE/"阅读导航_详细索引.md")=="4c959c39f6a5b221f9992f4a42a0fd222588d5a7e0d144b52f97fd0027e0217a" and all(s in (HERE/"00_阅读入口.md").read_text(encoding="utf-8") for s in ["按这条顺序读","一段能连贯叙述的网络汇报稿","单比特失真与恢复的理论","资料已整理好不等于已经确认你掌握了全部内容"]),
    old_quality_fail_preserved=audit["original_quality_status"]=="FAIL",
    teaching_mainline_recorded="2026-11-04 当前主线" in (ROOT/"AGENTS.md").read_text(encoding="utf-8"),
)
result=dict(status="PASS" if all(checks.values()) else "FAIL",
    scope="Teaching delivery only; no new quality approval, BIT build, training, or board test",
    checks=checks,documents=[p.name for p in mds],local_links_checked=links,
    frozen_files_checked=len(baseline),changed_sources=changed,broken_links=broken,
    images=images,visual_review="All eight scientific figures and desktop/narrow interactive screenshots viewed; labels and layout checked. Revised child-gate legend and final architecture heading/power path reviewed after repositioning.",
    source_statuses=dict(full_quality="FAIL retained",weak_correction="PASS existing",board_log="60 stored, 6 network completed, scoped PASS"),
    user_mastery="Ongoing; documents are not evidence that user has mastered the network")
(HERE/"reports/STANDARD_CHECK.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
if not all(checks.values()):raise SystemExit(1)
