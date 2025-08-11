from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict
from itertools import combinations

import sys


# 가능한 주사위 규칙들을 나타내는 enum
class DiceRule(Enum):
    ONE = 0
    TWO = 1
    THREE = 2
    FOUR = 3
    FIVE = 4
    SIX = 5
    CHOICE = 6
    FOUR_OF_A_KIND = 7
    FULL_HOUSE = 8
    SMALL_STRAIGHT = 9
    LARGE_STRAIGHT = 10
    YACHT = 11


# 입찰 방법을 나타내는 데이터클래스
@dataclass
class Bid:
    group: str  # 입찰 그룹 ('A' 또는 'B')
    amount: int  # 입찰 금액


# 주사위 배치 방법을 나타내는 데이터클래스
@dataclass
class DicePut:
    rule: DiceRule  # 배치 규칙
    dice: List[int]  # 배치할 주사위 목록


# 게임 상태를 관리하는 클래스
class Game:
    def __init__(self):
        self.my_state = GameState()  # 내 팀의 현재 상태
        self.opp_state = GameState()  # 상대 팀의 현재 상태

    # ================================ [수정된 코드] ================================
    def calculate_bid(self, dice_a: List[int], dice_b: List[int]) -> Bid:
        """
        주사위 그룹 A와 B의 잠재 가치를 나와 상대방 입장에서 모두 계산하여
        최적의 입찰 그룹과 금액을 결정합니다.
        """
        my_dice = self.my_state.dice
        opp_dice = self.opp_state.dice
        my_unused_rules = self.my_state.get_unused_rules()
        opp_unused_rules = self.opp_state.get_unused_rules()

        # 각 그룹의 잠재 가치 계산
        my_potential_A = self.my_state.calculate_potential_score(my_dice + dice_a, my_unused_rules)
        my_potential_B = self.my_state.calculate_potential_score(my_dice + dice_b, my_unused_rules)
        opp_potential_A = self.opp_state.calculate_potential_score(opp_dice + dice_a, opp_unused_rules)
        opp_potential_B = self.opp_state.calculate_potential_score(opp_dice + dice_b, opp_unused_rules)

        # 나와 상대가 선호하는 그룹 결정
        my_preferred_group = 'A' if my_potential_A > my_potential_B else 'B'
        opp_preferred_group = 'A' if opp_potential_A > opp_potential_B else 'B'

        my_gain = abs(my_potential_A - my_potential_B)
        amount = 0

        if my_preferred_group == opp_preferred_group:
            # 그룹이 겹칠 경우, 가치에 비례하여 입찰
            amount = my_gain // 4  # 기본적으로 이득의 1/4을 입찰

            # 점수 차이에 따라 입찰 성향 조절
            score_diff = self.my_state.get_total_score() - self.opp_state.get_total_score()
            if score_diff < -20000:  # 많이 지고 있을 때
                amount = my_gain // 2  # 공격적으로 절반 입찰
            elif score_diff > 20000:  # 많이 이기고 있을 때
                amount = my_gain // 8  # 수비적으로 입찰
        else:
            # 서로 다른 그룹을 원하면 0점 입찰
            amount = 0
        
        return Bid(my_preferred_group, max(0, min(100000, int(amount))))


    def calculate_put(self) -> DicePut:
        """
        현재 가진 주사위와 사용 가능한 규칙을 조합하여
        최고의 점수를 내거나, 점수가 낮을 경우 미래를 위해 희생하는 플레이를 선택합니다.
        """
        # is_sacrifice_ok=True를 통해 희생 플레이 전략 활성화
        best_put = self.my_state.find_best_put(self.my_state.dice, is_sacrifice_ok=True)
        return best_put
    # ============================== [수정된 코드 끝] ==============================

    def update_get(
        self,
        dice_a: List[int],
        dice_b: List[int],
        my_bid: Bid,
        opp_bid: Bid,
        my_group: str,
    ):
        """입찰 결과를 받아서 상태 업데이트"""
        if my_group == "A":
            self.my_state.add_dice(dice_a)
            self.opp_state.add_dice(dice_b)
        else:
            self.my_state.add_dice(dice_b)
            self.opp_state.add_dice(dice_a)

        my_bid_ok = my_bid.group == my_group
        self.my_state.bid(my_bid_ok, my_bid.amount)

        opp_group = "B" if my_group == "A" else "A"
        opp_bid_ok = opp_bid.group == opp_group
        self.opp_state.bid(opp_bid_ok, opp_bid.amount)

    def update_put(self, put: DicePut):
        """내가 주사위를 배치한 결과 반영"""
        self.my_state.use_dice(put)

    def update_set(self, put: DicePut):
        """상대가 주사위를 배치한 결과 반영"""
        self.opp_state.use_dice(put)


# 팀의 현재 상태를 관리하는 클래스
class GameState:
    def __init__(self):
        self.dice: List[int] = []
        self.rule_score: List[Optional[int]] = [None] * 12
        self.bid_score = 0

    def get_total_score(self) -> int:
        """현재까지 획득한 총 점수 계산"""
        basic = sum(score for score in self.rule_score[0:6] if score is not None)
        bonus = 35000 if basic >= 63000 else 0
        combination = sum(score for score in self.rule_score[6:12] if score is not None)
        return basic + bonus + combination + self.bid_score

    def bid(self, is_successful: bool, amount: int):
        """입찰 결과에 따른 점수 반영"""
        self.bid_score += -amount if is_successful else amount

    def add_dice(self, new_dice: List[int]):
        """새로운 주사위들을 보유 목록에 추가"""
        self.dice.extend(new_dice)

    def use_dice(self, put: DicePut):
        """주사위를 사용하여 특정 규칙에 배치"""
        assert put.rule is not None and self.rule_score[put.rule.value] is None, "Rule already used"
        for d in put.dice:
            self.dice.remove(d)
        self.rule_score[put.rule.value] = self.calculate_score(put)

    # ================================ [추가된 헬퍼 함수] ================================
    def get_unused_rules(self) -> List[DiceRule]:
        """사용하지 않은 규칙 목록 반환"""
        return [DiceRule(i) for i, score in enumerate(self.rule_score) if score is None]

    def find_best_put(self, dice_pool: List[int], is_sacrifice_ok: bool = False) -> DicePut:
        """
        주어진 주사위 풀에서 최적의 (규칙, 주사위) 조합을 찾습니다.
        is_sacrifice_ok가 True이면, 낮은 점수일 경우 희생 플레이를 고려합니다.
        """
        unused_rules = self.get_unused_rules()
        if not unused_rules:
            return DicePut(DiceRule.CHOICE, dice_pool[:5])

        possible_plays: List[Dict] = []
        num_dice_to_choose = min(len(dice_pool), 5)

        for hand_tuple in combinations(dice_pool, num_dice_to_choose):
            hand = list(hand_tuple)
            for rule in unused_rules:
                score = self.calculate_score(DicePut(rule, hand))
                possible_plays.append({'score': score, 'rule': rule, 'dice': hand})

        if not possible_plays:
            return DicePut(unused_rules[0], dice_pool[:5])
        
        best_play = max(possible_plays, key=lambda p: p['score'])

        # 희생 플레이 전략
        if is_sacrifice_ok and best_play['score'] < 10000:
            sacrifice_priority = [
                DiceRule.YACHT, DiceRule.LARGE_STRAIGHT, DiceRule.FOUR_OF_A_KIND,
                DiceRule.SMALL_STRAIGHT, DiceRule.FULL_HOUSE, DiceRule.ONE, DiceRule.TWO
            ]
            for rule_to_sacrifice in sacrifice_priority:
                if rule_to_sacrifice in unused_rules:
                    # 해당 규칙으로 0점을 기록할 수 있는 조합을 찾아 희생
                    for play in possible_plays:
                        if play['rule'] == rule_to_sacrifice and play['score'] == 0:
                            return DicePut(play['rule'], play['dice'])
        
        return DicePut(best_play['rule'], best_play['dice'])

    def calculate_potential_score(self, dice_pool: List[int], unused_rules: List[DiceRule]) -> int:
        """
        주어진 주사위 풀과 미사용 규칙으로 얻을 수 있는 최대 잠재 점수를 계산합니다.
        """
        best_score = 0
        num_dice_to_choose = min(len(dice_pool), 5)
        
        # 조합 수가 너무 많아지면 샘플링 (시간 초과 방지)
        all_combinations = list(combinations(dice_pool, num_dice_to_choose))
        if len(all_combinations) > 300: # C(10,5)=252, C(12,5)=792
            import random
            all_combinations = random.sample(all_combinations, 300)

        for hand_tuple in all_combinations:
            hand = list(hand_tuple)
            for rule in unused_rules:
                score = self.calculate_score(DicePut(rule, hand))
                if score > best_score:
                    best_score = score
        return best_score
    # ============================== [추가된 헬퍼 함수 끝] ==============================

    @staticmethod
    def calculate_score(put: DicePut) -> int:
        """규칙에 따른 점수를 계산하는 함수 (FULL_HOUSE 로직 수정)"""
        rule, dice = put.rule, put.dice
        counts = [dice.count(i) for i in range(1, 7)]

        if rule == DiceRule.ONE: return dice.count(1) * 1 * 1000
        if rule == DiceRule.TWO: return dice.count(2) * 2 * 1000
        if rule == DiceRule.THREE: return dice.count(3) * 3 * 1000
        if rule == DiceRule.FOUR: return dice.count(4) * 4 * 1000
        if rule == DiceRule.FIVE: return dice.count(5) * 5 * 1000
        if rule == DiceRule.SIX: return dice.count(6) * 6 * 1000
        if rule == DiceRule.CHOICE: return sum(dice) * 1000
        if rule == DiceRule.FOUR_OF_A_KIND:
            return sum(dice) * 1000 if any(c >= 4 for c in counts) else 0
        if rule == DiceRule.FULL_HOUSE:
            # 정확한 Full House 로직: 3개, 2개 조합
            return sum(dice) * 1000 if (3 in counts and 2 in counts) else 0
        if rule == DiceRule.SMALL_STRAIGHT:
            straights = [[1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]]
            dice_set = set(dice)
            for s in straights:
                if set(s).issubset(dice_set): return 15000
            return 0
        if rule == DiceRule.LARGE_STRAIGHT:
            dice_str = "".join(map(str, sorted(dice)))
            return 30000 if dice_str in ["12345", "23456"] else 0
        if rule == DiceRule.YACHT:
            return 50000 if any(c == 5 for c in counts) else 0

        assert False, "Invalid rule"


def main():
    game = Game()
    dice_a, dice_b = [0] * 5, [0] * 5
    my_bid = Bid("", 0)

    while True:
        try:
            line = sys.stdin.readline().strip()
            if not line:
                continue

            command, *args = line.split()

            if command == "READY":
                print("OK")
                sys.stdout.flush()
            elif command == "ROLL":
                str_a, str_b = args
                dice_a = [int(c) for c in str_a]
                dice_b = [int(c) for c in str_b]
                my_bid = game.calculate_bid(dice_a, dice_b)
                print(f"BID {my_bid.group} {my_bid.amount}")
                sys.stdout.flush()
            elif command == "GET":
                get_group, opp_group, opp_score_str = args
                opp_score = int(opp_score_str)
                game.update_get(dice_a, dice_b, my_bid, Bid(opp_group, opp_score), get_group)
            elif command == "SCORE":
                put = game.calculate_put()
                game.update_put(put)
                assert put.rule is not None
                dice_str = ''.join(map(str, sorted(put.dice)))
                print(f"PUT {put.rule.name} {dice_str}")
                sys.stdout.flush()
            elif command == "SET":
                rule_name, str_dice = args
                dice = [int(c) for c in str_dice]
                game.update_set(DicePut(DiceRule[rule_name], dice))
            elif command == "FINISH":
                break

        except EOFError:
            break


if __name__ == "__main__":
    main()