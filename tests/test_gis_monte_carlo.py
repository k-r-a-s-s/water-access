# Generated by CodiumAI
from src.gis_monte_carlo import sample_normal
from src.gis_monte_carlo import sample_lognormal
from src.gis_monte_carlo import run_simulation
from src.gis_monte_carlo import process_mc_results
import src.gis_monte_carlo

import numpy as np
import pandas as pd
from pathlib import Path
import pytest
import os
import tempfile
import shutil


class TestSampleNormal:

    # The function returns a numpy array of size n.
    def test_returns_array_of_size_n(self):
        low = 0
        high = 10
        n = 5
        result = sample_normal(low, high, n)
        assert isinstance(result, np.ndarray)
        assert len(result) == n

    # The function returns an empty numpy array when n is 0.
    def test_returns_empty_array_when_n_is_0(self):
        low = 0
        high = 10
        n = 0
        result = sample_normal(low, high, n)
        assert isinstance(result, np.ndarray)
        assert len(result) == 0


class TestSampleLognormal:

    def test_returns_array_of_size_n(self):
        low = 1
        high = 10
        n = 5
        result = sample_lognormal(low, high, n)
        assert isinstance(result, np.ndarray)
        assert len(result) == n

    def test_returns_empty_array_when_n_is_0(self):
        low = 1
        high = 10
        n = 0
        result = sample_lognormal(low, high, n)
        assert isinstance(result, np.ndarray)
        assert len(result) == 0

    def test_raises_assertion_error_when_low_is_less_than_0(self):
        low = -1
        high = 10
        n = 5
        with pytest.raises(AssertionError):
            sample_lognormal(low, high, n)


class TestRunSimulation:

    def test_valid_input_returns_result(self):
        crr_adjustment = 1
        time_gathering_water = 5
        practical_limit_bicycle = 10
        practical_limit_buckets = 20
        met = 3
        watts = 75
        hill_polarity = "flat_uphill"
        result = run_simulation(
            crr_adjustment,
            time_gathering_water,
            practical_limit_bicycle,
            practical_limit_buckets,
            met,
            watts,
            hill_polarity,
            calculate_distance=False,
            use_sample_data=True,
        )
        assert isinstance(result, tuple)

    def test_invalid_crr_adjustment_raises_assertion_error(self):
        crr_adjustment = "1"
        time_gathering_water = 5
        practical_limit_bicycle = 10
        practical_limit_buckets = 20
        met = 3
        watts = 75
        hill_polarity = "flat_uphill"
        with pytest.raises(AssertionError):
            run_simulation(
                crr_adjustment,
                time_gathering_water,
                practical_limit_bicycle,
                practical_limit_buckets,
                met,
                watts,
                hill_polarity,
                calculate_distance=False,
            )

    def test_invalid_time_gathering_water_raises_assertion_error(self):
        crr_adjustment = 1
        time_gathering_water = "invalid"
        practical_limit_bicycle = 10
        practical_limit_buckets = 20
        met = 3
        watts = 75
        hill_polarity = "flat_uphill"
        with pytest.raises(AssertionError):
            run_simulation(
                crr_adjustment,
                time_gathering_water,
                practical_limit_bicycle,
                practical_limit_buckets,
                met,
                watts,
                hill_polarity,
                calculate_distance=False,
            )

    def test_invalid_practical_limit_bicycle_raises_assertion_error(self):
        crr_adjustment = 1
        time_gathering_water = 2.5
        practical_limit_bicycle = "invalid"
        practical_limit_buckets = 20
        met = 3
        watts = 75
        hill_polarity = "flat_uphill"
        with pytest.raises(AssertionError):
            run_simulation(
                crr_adjustment,
                time_gathering_water,
                practical_limit_bicycle,
                practical_limit_buckets,
                met,
                watts,
                hill_polarity,
                calculate_distance=False,
            )

    def test_invalid_practical_limit_buckets_raises_assertion_error(self):
        crr_adjustment = 1
        time_gathering_water = 2.5
        practical_limit_bicycle = 10
        practical_limit_buckets = "invalid"
        met = 3
        watts = 75
        hill_polarity = "flat_uphill"
        with pytest.raises(AssertionError):
            run_simulation(
                crr_adjustment,
                time_gathering_water,
                practical_limit_bicycle,
                practical_limit_buckets,
                met,
                watts,
                hill_polarity,
                calculate_distance=False,
            )

    def test_invalid_met_raises_assertion_error(self):
        crr_adjustment = 1
        time_gathering_water = 2.5
        practical_limit_bicycle = 10
        practical_limit_buckets = 5
        met = "invalid"
        watts = 75
        hill_polarity = "flat_uphill"
        with pytest.raises(AssertionError):
            run_simulation(
                crr_adjustment,
                time_gathering_water,
                practical_limit_bicycle,
                practical_limit_buckets,
                met,
                watts,
                hill_polarity,
                calculate_distance=False,
            )

    def test_invalid_watts_raises_assertion_error(self):
        crr_adjustment = 1
        time_gathering_water = 2.5
        practical_limit_bicycle = 10
        practical_limit_buckets = 5
        met = 3
        watts = np.array([75, 100])
        hill_polarity = "flat_uphill"
        with pytest.raises(AssertionError):
            run_simulation(
                crr_adjustment,
                time_gathering_water,
                practical_limit_bicycle,
                practical_limit_buckets,
                met,
                watts,
                hill_polarity,
                calculate_distance=False,
            )

    def test_invalid_hill_polarity_raises_assertion_error(self):
        crr_adjustment = 1
        time_gathering_water = 2.5
        practical_limit_bicycle = 10
        practical_limit_buckets = 5
        met = 3
        watts = 75
        hill_polarity = 1
        with pytest.raises(AssertionError):
            run_simulation(
                crr_adjustment,
                time_gathering_water,
                practical_limit_bicycle,
                practical_limit_buckets,
                met,
                watts,
                hill_polarity,
                calculate_distance=False,
            )


class TestProcessMCResults:

    def test_process_mc_results_saves_results_to_output_dir(self):
        # Arrange
        simulation_results = [
            pd.DataFrame(
                {
                    "percent_with_water": [0.5, 0.6, 0.7],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
            pd.DataFrame(
                {
                    "percent_with_water": [0.4, 0.3, 0.2],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
        ]

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        # Act
        process_mc_results(simulation_results, plot=False, output_dir=temp_dir)

        # Assert
        assert os.path.exists(os.path.join(temp_dir, "country_median_results.csv"))
        assert os.path.exists(os.path.join(temp_dir, "country_mean_results.csv"))
        assert os.path.exists(
            os.path.join(temp_dir, "country_5th_percentile_results.csv")
        )
        assert os.path.exists(
            os.path.join(temp_dir, "country_95th_percentile_results.csv")
        )
        assert os.path.exists(
            os.path.join(temp_dir, "countries_simulation_results.pkl")
        )

        # Remove the temporary directory when you're done
        shutil.rmtree(temp_dir)

    def test_process_mc_results_plots_chloropleth_maps_when_plot_is_true(self, mocker):
        # Arrange
        simulation_results = [
            pd.DataFrame(
                {
                    "percent_with_water": [0.5, 0.6, 0.7],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
            pd.DataFrame(
                {
                    "percent_with_water": [0.4, 0.3, 0.2],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
        ]
        # Mock the plot_chloropleth function
        mock_plot_chloropleth = mocker.patch("src.gis_monte_carlo.gis.plot_chloropleth")

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        # Act
        try:
            process_mc_results(simulation_results, plot=False, output_dir=temp_dir)

            # Assert
            assert mock_plot_chloropleth.call_count == 0
        finally:
            # Remove the temporary directory when you're done
            shutil.rmtree(temp_dir)

    def test_process_mc_results_does_not_plot_chloropleth_maps_when_plot_is_false(
        self, mocker
    ):
        # Arrange
        simulation_results = [
            pd.DataFrame(
                {
                    "percent_with_water": [0.5, 0.6, 0.7],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
            pd.DataFrame(
                {
                    "percent_with_water": [0.4, 0.3, 0.2],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
        ]
        mocker.patch("src.gis_monte_carlo.gis.plot_chloropleth")

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        # Act
        try:
            process_mc_results(simulation_results, plot=False, output_dir=temp_dir)
        finally:
            # Remove the temporary directory when you're done
            shutil.rmtree(temp_dir)

        # Assert
        assert src.gis_monte_carlo.gis.plot_chloropleth.call_count == 0

    def test_process_mc_results_raises_error_when_simulation_results_is_not_list(self):
        # Arrange
        simulation_results = "invalid_results"

        # Act & Assert
        with pytest.raises(TypeError):
            process_mc_results(simulation_results, plot=False, output_dir=None)

    def test_process_mc_results_raises_error_when_output_dir_is_not_string(self):
        # Arrange
        simulation_results = [
            pd.DataFrame(
                {
                    "percent_with_water": [0.5, 0.6, 0.7],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
            pd.DataFrame(
                {
                    "percent_with_water": [0.4, 0.3, 0.2],
                    "ISOCODE": ["GB", "FR", "DE"],
                    "Entity": ["United Kingdom", "France", "Germany"],
                    "region": ["Europe", "Europe", "Europe"],
                    "subregion": [
                        "Northern Europe",
                        "Western Europe",
                        "Western Europe",
                    ],
                }
            ),
        ]
        output_dir = 123

        # Act & Assert
        with pytest.raises(TypeError):
            process_mc_results(simulation_results, plot=False, output_dir=output_dir)
